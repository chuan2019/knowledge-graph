from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class AppRoutesIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.verify_connectivity = patch(
            "app.services.graph_store.GraphStore.verify_connectivity",
            return_value=None,
        )
        self.verify_connectivity.start()

    def tearDown(self) -> None:
        self.verify_connectivity.stop()

    def test_root_serves_browser_ui(self) -> None:
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Knowledge Graph QA", response.text)

    def test_health_returns_service_configuration(self) -> None:
        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("neo4j", response.json())
        self.assertIn("ollama_base_url", response.json())

    def test_schema_routes_return_graph_schema(self) -> None:
        with TestClient(app) as client:
            legacy_response = client.get("/schema")
            versioned_response = client.get("/api/v1/schema")

        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(versioned_response.status_code, 200)
        self.assertIn("graph_schema", legacy_response.json())
        self.assertEqual(legacy_response.json(), versioned_response.json())

    def test_metrics_routes_return_request_counters(self) -> None:
        with TestClient(app) as client:
            client.get("/health")
            legacy_response = client.get("/metrics")
            versioned_response = client.get("/api/v1/metrics")

        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(versioned_response.status_code, 200)
        self.assertIn("total_requests", legacy_response.json())
        self.assertIn("paths", legacy_response.json())
        self.assertGreaterEqual(
            versioned_response.json()["total_requests"],
            legacy_response.json()["total_requests"],
        )
        self.assertTrue(
            any(item["path"] == "/health" for item in legacy_response.json()["paths"])
        )
        self.assertTrue(
            any(item["path"] == "/metrics" for item in versioned_response.json()["paths"])
        )
        self.assertIn("X-Response-Time", legacy_response.headers)

    def test_legacy_ask_route_returns_stubbed_answer(self) -> None:
        with TestClient(app) as client:
            app.state.qa_service.answer_question = AsyncMock(
                return_value=(
                    "stub answer",
                    "MATCH (n) RETURN n LIMIT 1",
                    [{"name": "stub"}],
                    ["Received user question.", "Synthesized natural-language answer."],
                )
            )
            response = client.post(
                "/api/ask",
                json={"question": "test question", "include_rows": True},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "stub answer")
        self.assertEqual(response.json()["row_count"], 1)

    def test_versioned_ask_route_can_hide_rows(self) -> None:
        with TestClient(app) as client:
            app.state.qa_service.answer_question = AsyncMock(
                return_value=(
                    "stub answer",
                    "MATCH (n) RETURN n LIMIT 1",
                    [{"name": "stub"}],
                    ["Received user question.", "Synthesized natural-language answer."],
                )
            )
            response = client.post(
                "/api/v1/ask",
                json={"question": "test question", "include_rows": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "stub answer")
        self.assertEqual(response.json()["rows"], [])
        self.assertEqual(response.json()["row_count"], 1)

    def test_ask_route_returns_structured_error_payload(self) -> None:
        with TestClient(app, raise_server_exceptions=False) as client:
            app.state.qa_service.answer_question = AsyncMock(
                side_effect=RuntimeError("planner failure")
            )
            response = client.post(
                "/api/v1/ask",
                json={"question": "test question", "include_rows": False},
            )

            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json()["error"], "Internal server error")
            self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
