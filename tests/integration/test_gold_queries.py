"""Integration tests: run gold Cypher queries against a live Neo4j instance.

These tests require the demo stack to be running:

    docker compose --profile all up

Skip gracefully when Neo4j is not reachable so the suite can run in CI
environments without the database.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml
from neo4j import AsyncGraphDatabase

from app.core.config import Settings

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class GoldQueryIntegrationTestCase(unittest.IsolatedAsyncioTestCase):
    """Verify that each gold Cypher query executes without error and returns
    the expected result shape against the live demo Neo4j database."""

    driver: Any = None

    async def asyncSetUp(self) -> None:
        settings = Settings.from_env()
        try:
            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            await driver.verify_connectivity()
            self.driver = driver
            self.database = settings.neo4j_database
        except Exception:
            self.driver = None

    async def asyncTearDown(self) -> None:
        if self.driver is not None:
            await self.driver.close()

    def _load_gold_queries(self) -> list[dict]:
        path = FIXTURES_DIR / "gold_queries.yaml"
        return yaml.safe_load(path.read_text())

    async def test_gold_queries_return_expected_shape(self) -> None:
        """Each gold query must run without error and return the expected columns."""
        if self.driver is None:
            self.skipTest(
                "Neo4j is not reachable — start the stack with "
                "'docker compose --profile all up' before running integration tests."
            )

        gold_queries = self._load_gold_queries()

        for gq in gold_queries:
            with self.subTest(id=gq["id"]):
                async with self.driver.session(database=self.database) as session:
                    result = await session.run(gq["cypher"])
                    rows = await result.data()

                min_rows = gq.get("min_rows", 1)
                self.assertGreaterEqual(
                    len(rows),
                    min_rows,
                    f"[{gq['id']}] expected at least {min_rows} row(s), "
                    f"got {len(rows)}.\nQuery:\n{gq['cypher']}",
                )

                expected_cols: list[str] = gq.get("expected_columns", [])
                if rows and expected_cols:
                    for col in expected_cols:
                        self.assertIn(
                            col,
                            rows[0],
                            f"[{gq['id']}] column '{col}' missing from result. "
                            f"Got columns: {list(rows[0].keys())}",
                        )

    async def test_gold_queries_match_question_intent(self) -> None:
        """Spot-check: each query returns rows that are plausibly relevant
        to the natural-language question (non-empty result for min_rows >= 1)."""
        if self.driver is None:
            self.skipTest("Neo4j is not reachable.")

        gold_queries = self._load_gold_queries()
        skipped: list[str] = []
        failures: list[str] = []

        for gq in gold_queries:
            if gq.get("min_rows", 1) == 0:
                skipped.append(gq["id"])
                continue

            async with self.driver.session(database=self.database) as session:
                result = await session.run(gq["cypher"])
                rows = await result.data()

            if not rows:
                failures.append(
                    f"  [{gq['id']}] returned 0 rows for: {gq['question']}"
                )

        if failures:
            self.fail(
                "The following gold queries returned no results — "
                "the demo data may be missing or the query is incorrect:\n"
                + "\n".join(failures)
            )

        if skipped:
            print(f"\n  (skipped date-window check for: {', '.join(skipped)})")


if __name__ == "__main__":
    unittest.main()
