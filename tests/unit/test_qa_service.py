from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from neo4j.exceptions import CypherSyntaxError

from app.core.config import Settings
from app.services.qa_service import GraphQAService


class GraphQAServiceUnitTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings(max_query_retries=1, result_row_limit=3)
        self.graph_store = MagicMock()
        self.ollama_client = MagicMock()
        self.service = GraphQAService(self.settings, self.graph_store, self.ollama_client)

    async def test_answer_question_returns_answer_and_trace(self) -> None:
        self.ollama_client.generate_json = AsyncMock(
            return_value={"cypher": "MATCH (n) RETURN n LIMIT 1", "rationale": "stub"}
        )
        self.graph_store.run_read_query.return_value = [{"name": "alpha"}]
        self.ollama_client.generate_text = AsyncMock(return_value="Grounded answer")

        answer, cypher, rows, trace = await self.service.answer_question("test question")

        self.assertEqual(answer, "Grounded answer")
        self.assertEqual(cypher, "MATCH (n) RETURN n LIMIT 1")
        self.assertEqual(rows, [{"name": "alpha"}])
        self.assertIn("Planned Cypher on attempt 1.", trace)
        self.assertIn("Synthesized natural-language answer.", trace)

    async def test_answer_question_retries_after_query_failure(self) -> None:
        self.ollama_client.generate_json = AsyncMock(
            side_effect=[
                {"cypher": "MATCH (n RETURN n", "rationale": "broken"},
                {"cypher": "MATCH (n) RETURN n LIMIT 1", "rationale": "fixed"},
            ]
        )
        self.graph_store.run_read_query.side_effect = [
            CypherSyntaxError("bad query"),
            [{"name": "alpha"}],
        ]
        self.ollama_client.generate_text = AsyncMock(return_value="Recovered answer")

        answer, cypher, rows, trace = await self.service.answer_question("test question")

        self.assertEqual(answer, "Recovered answer")
        self.assertEqual(cypher, "MATCH (n) RETURN n LIMIT 1")
        self.assertEqual(rows, [{"name": "alpha"}])
        self.assertTrue(any("failed on attempt 1" in step for step in trace))
        self.assertEqual(self.ollama_client.generate_json.await_count, 2)

    async def test_answer_question_logs_retry_failures(self) -> None:
        self.ollama_client.generate_json = AsyncMock(
            side_effect=[
                {"cypher": "MATCH (n RETURN n", "rationale": "broken"},
                {"cypher": "MATCH (n) RETURN n LIMIT 1", "rationale": "fixed"},
            ]
        )
        self.graph_store.run_read_query.side_effect = [
            ValueError("bad query"),
            [{"name": "alpha"}],
        ]
        self.ollama_client.generate_text = AsyncMock(return_value="Recovered answer")

        with self.assertLogs("app.services.qa_service", level="DEBUG") as captured:
            await self.service.answer_question("test question")

        self.assertTrue(
            any("Cypher execution failed on attempt 1: bad query" in message for message in captured.output)
        )

    async def test_answer_question_raises_after_exhausted_retries(self) -> None:
        self.ollama_client.generate_json = AsyncMock(
            return_value={"cypher": "MATCH (n RETURN n", "rationale": "broken"}
        )
        self.graph_store.run_read_query.side_effect = ValueError("still bad")

        with self.assertRaisesRegex(RuntimeError, "Unable to answer question"):
            await self.service.answer_question("test question")

    async def test_summarize_answer_short_circuits_when_no_rows(self) -> None:
        response = await self.service._summarize_answer(
            question="test question",
            cypher="MATCH (n) RETURN n LIMIT 1",
            rows=[],
            model=None,
        )

        self.assertEqual(
            response,
            "I could not find matching records in the graph for that question.",
        )


if __name__ == "__main__":
    unittest.main()
