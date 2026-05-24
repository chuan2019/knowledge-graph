from __future__ import annotations

import re
from typing import Any

from neo4j import GraphDatabase, Query

from app.config import Settings

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


class GraphStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def close(self) -> None:
        self._driver.close()

    def run_read_query(self, query: str) -> list[dict[str, Any]]:
        safe_query = self._ensure_safe_read_query(query)
        with self._driver.session(database=self._settings.neo4j_database) as session:
            result = session.run(
                Query(
                    safe_query,
                    timeout=self._settings.cypher_timeout_ms / 1000,
                )
            )
            rows = [dict(record.items()) for record in result]
        return rows

    def _ensure_safe_read_query(self, query: str) -> str:
        normalized_query = query.strip().rstrip(";")
        if not normalized_query:
            raise ValueError("Generated Cypher query is empty.")

        upper_query = normalized_query.upper()
        for pattern in FORBIDDEN_CYPHER_PATTERNS:
            if re.search(pattern, upper_query):
                raise ValueError(
                    "Generated Cypher contains write or admin operations, which are not allowed."
                )

        if "RETURN" not in upper_query:
            raise ValueError("Generated Cypher must include a RETURN clause.")

        if "LIMIT" not in upper_query:
            normalized_query = (
                f"{normalized_query}\nLIMIT {self._settings.result_row_limit}"
            )

        return normalized_query
