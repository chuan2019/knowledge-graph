from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import Settings
from app.services.graph_store import GraphStore


class GraphStoreUnitTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.driver = MagicMock()
        self.driver.close = AsyncMock(return_value=None)
        self.driver.verify_connectivity = AsyncMock(return_value=None)
        self.driver_patch = patch(
            "app.services.graph_store.AsyncGraphDatabase.driver",
            return_value=self.driver,
        )
        self.driver_patch.start()
        self.settings = Settings(result_row_limit=7)
        self.store = GraphStore(self.settings)

    async def asyncTearDown(self) -> None:
        await self.store.close()
        self.driver_patch.stop()

    async def test_safe_query_appends_limit_when_missing(self) -> None:
        query = self.store._ensure_safe_read_query("MATCH (n) RETURN n")
        self.assertEqual(query, "MATCH (n) RETURN n\nLIMIT 7")

    async def test_safe_query_rejects_write_operations(self) -> None:
        with self.assertRaisesRegex(ValueError, "write or admin operations"):
            self.store._ensure_safe_read_query("MATCH (n) DELETE n RETURN n")

    async def test_safe_query_requires_return(self) -> None:
        with self.assertRaisesRegex(ValueError, "RETURN clause"):
            self.store._ensure_safe_read_query("MATCH (n)")

    async def test_safe_query_rewrites_legacy_exists_pattern(self) -> None:
        query = self.store._ensure_safe_read_query(
            """
            MATCH (v:Version)
            WHERE EXISTS((dr:DeliveryRequest)-[:FOR_VERSION]->(v))
            RETURN v.version_id
            """
        )

        self.assertIn(
            "EXISTS { MATCH (dr:DeliveryRequest)-[:FOR_VERSION]->(v) }",
            query,
        )
        self.assertNotIn("EXISTS((dr:DeliveryRequest)-[:FOR_VERSION]->(v))", query)

    async def test_safe_query_rewrites_bare_pattern_lines_inside_exists_block(self) -> None:
        query = self.store._ensure_safe_read_query(
            """
            MATCH (t:Title)-[:HAS_VERSION]->(v:Version)
            WHERE EXISTS {
                MATCH (dr:DeliveryRequest)-[:TO_POINT]->(dp)
                (dp:DeliveryPoint)-[:LOCATED_IN]->(r)
            }
            RETURN t.title_name
            """
        )

        self.assertIn(
            "MATCH (dp:DeliveryPoint)-[:LOCATED_IN]->(r)",
            query,
        )
        self.assertNotIn(
            "\n                (dp:DeliveryPoint)-[:LOCATED_IN]->(r)",
            query,
        )

    async def test_safe_query_logs_normalization_when_query_is_rewritten(self) -> None:
        with self.assertLogs("app.services.graph_store", level="DEBUG") as captured:
            self.store._ensure_safe_read_query(
                """
                MATCH (v:Version)
                WHERE EXISTS((dr:DeliveryRequest)-[:FOR_VERSION]->(v))
                RETURN v.version_id
                """
            )

        self.assertTrue(
            any("Normalized generated Cypher before execution" in message for message in captured.output)
        )

    async def test_run_read_query_uses_session_and_returns_rows(self) -> None:
        session = MagicMock()
        result = MagicMock()
        result.data = AsyncMock(return_value=[{"name": "alpha"}, {"name": "beta"}])
        session.run = AsyncMock(return_value=result)
        self.driver.session.return_value.__aenter__.return_value = session

        rows = await self.store.run_read_query("MATCH (n) RETURN n.name AS name")

        self.assertEqual(rows, [{"name": "alpha"}, {"name": "beta"}])
        self.driver.session.assert_called_once_with(database=self.settings.neo4j_database)
        session.run.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
