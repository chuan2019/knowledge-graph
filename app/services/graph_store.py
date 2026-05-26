from __future__ import annotations

import logging
import re
import time
from typing import Any, LiteralString, cast

from neo4j import AsyncGraphDatabase, Query
from opentelemetry import trace

from app.core.config import Settings
from app.core.middleware import MetricsRegistry

FORBIDDEN_CYPHER_PATTERNS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bDETACH\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bDROP\b",
    r"\bLOAD\s+CSV\b",
    r"\bCALL\s+dbms\b",
    r"\bCALL\s+apoc\.periodic\b",
]

LEGACY_EXISTS_PATTERN = re.compile(
    r"EXISTS\s*\(\s*(?P<pattern>\([^()]*\)(?:\s*(?:<?-\[[^\]]*\]-?>|<?--?>)\s*\([^()]*\))+?)\s*\)",
    flags=re.IGNORECASE | re.DOTALL,
)
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class GraphStore:
    def __init__(self, settings: Settings, metrics_registry: MetricsRegistry | None = None) -> None:
        self._settings = settings
        self._metrics_registry = metrics_registry
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=settings.neo4j_max_connection_pool_size,
        )

    async def verify_connectivity(self) -> None:
        logger.debug("Verifying Neo4j driver connectivity to %s", self._settings.neo4j_uri)
        await self._driver.verify_connectivity()
        logger.info("Neo4j connectivity verified for database=%s", self._settings.neo4j_database)

    async def close(self) -> None:
        logger.debug("Closing Neo4j driver")
        await self._driver.close()

    async def run_read_query(self, query: str) -> list[dict[str, Any]]:
        with tracer.start_as_current_span("neo4j.run_read_query") as span:
            safe_query = self._ensure_safe_read_query(query)
            span.set_attribute("db.system", "neo4j")
            span.set_attribute("db.operation", "read")
            span.set_attribute("db.query_length", len(safe_query))
            logger.debug("Executing read query against Neo4j: %s", safe_query)
            start = time.perf_counter()
            try:
                async with self._driver.session(database=self._settings.neo4j_database) as session:
                    result = await session.run(
                        Query(
                            cast(LiteralString, safe_query),
                            timeout=self._settings.cypher_timeout_ms / 1000,
                        )
                    )
                    rows = await result.data()
            except Exception:
                duration_ms = (time.perf_counter() - start) * 1000
                if self._metrics_registry is not None:
                    self._metrics_registry.record_neo4j_query(
                        outcome="error",
                        duration_ms=duration_ms,
                    )
                raise

            duration_ms = (time.perf_counter() - start) * 1000
            if self._metrics_registry is not None:
                self._metrics_registry.record_neo4j_query(
                    outcome="success",
                    duration_ms=duration_ms,
                    row_count=len(rows),
                )
            span.set_attribute("db.row_count", len(rows))
            logger.debug(
                "Neo4j query completed: rows=%s duration_ms=%.3f",
                len(rows),
                duration_ms,
            )
            return rows

    def _ensure_safe_read_query(self, query: str) -> str:
        normalized_query = query.strip().rstrip(";")
        if not normalized_query:
            raise ValueError("Generated Cypher query is empty.")

        original_query = normalized_query
        normalized_query = self._rewrite_legacy_exists_patterns(normalized_query)
        normalized_query = self._rewrite_bare_pattern_lines(normalized_query)

        if normalized_query != original_query:
            logger.debug(
                "Normalized generated Cypher before execution. original=%s normalized=%s",
                original_query,
                normalized_query,
            )

        upper_query = normalized_query.upper()
        for pattern in FORBIDDEN_CYPHER_PATTERNS:
            if re.search(pattern, upper_query):
                logger.warning("Rejected unsafe Cypher due to forbidden pattern: %s", pattern)
                raise ValueError(
                    "Generated Cypher contains write or admin operations, which are not allowed."
                )

        if "RETURN" not in upper_query:
            logger.warning("Rejected Cypher without RETURN clause: %s", normalized_query)
            raise ValueError("Generated Cypher must include a RETURN clause.")

        if "LIMIT" not in upper_query:
            normalized_query = (
                f"{normalized_query}\nLIMIT {self._settings.result_row_limit}"
            )
            logger.debug(
                "Appended default LIMIT %s to generated Cypher",
                self._settings.result_row_limit,
            )

        return normalized_query

    def _rewrite_legacy_exists_patterns(self, query: str) -> str:
        def replacer(match: re.Match[str]) -> str:
            pattern = match.group("pattern").strip()
            return f"EXISTS {{ MATCH {pattern} }}"

        return LEGACY_EXISTS_PATTERN.sub(replacer, query)

    def _rewrite_bare_pattern_lines(self, query: str) -> str:
        normalized_lines: list[str] = []
        previous_significant_line = ""

        for line in query.splitlines():
            stripped_line = line.strip()

            if stripped_line.startswith("(") and not self._is_pattern_continuation(
                previous_significant_line
            ):
                indent = line[: len(line) - len(line.lstrip())]
                line = f"{indent}MATCH {stripped_line}"
                stripped_line = line.strip()

            normalized_lines.append(line)

            if stripped_line:
                previous_significant_line = stripped_line

        return "\n".join(normalized_lines)

    @staticmethod
    def _is_pattern_continuation(previous_significant_line: str) -> bool:
        previous = previous_significant_line.rstrip()
        return previous.endswith(("->", "<-", "-", ",", "("))
