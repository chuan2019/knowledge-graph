from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.services.graph_store import GraphStore


class GraphStoreUnitTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = MagicMock()
        self.driver_patch = patch(
            "app.services.graph_store.GraphDatabase.driver",
            return_value=self.driver,
        )
        self.driver_patch.start()
        self.settings = Settings(result_row_limit=7)
        self.store = GraphStore(self.settings)

    def tearDown(self) -> None:
        self.store.close()
        self.driver_patch.stop()

    def test_safe_query_appends_limit_when_missing(self) -> None:
        query = self.store._ensure_safe_read_query("MATCH (n) RETURN n")
        self.assertEqual(query, "MATCH (n) RETURN n\nLIMIT 7")

    def test_safe_query_rejects_write_operations(self) -> None:
        with self.assertRaisesRegex(ValueError, "write or admin operations"):
            self.store._ensure_safe_read_query("MATCH (n) DELETE n RETURN n")

    def test_safe_query_requires_return(self) -> None:
        with self.assertRaisesRegex(ValueError, "RETURN clause"):
            self.store._ensure_safe_read_query("MATCH (n)")

    def test_run_read_query_uses_session_and_returns_rows(self) -> None:
        session = MagicMock()
        session.run.return_value = [
            MagicMock(items=MagicMock(return_value=[("name", "alpha")])),
            MagicMock(items=MagicMock(return_value=[("name", "beta")])),
        ]
        self.driver.session.return_value.__enter__.return_value = session

        rows = self.store.run_read_query("MATCH (n) RETURN n.name AS name")

        self.assertEqual(rows, [{"name": "alpha"}, {"name": "beta"}])
        self.driver.session.assert_called_once_with(database=self.settings.neo4j_database)
        session.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
