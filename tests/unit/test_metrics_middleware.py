from __future__ import annotations

import unittest

from app.core.middleware import MetricsRegistry


class MetricsRegistryUnitTestCase(unittest.TestCase):
    def test_snapshot_tracks_requests_status_and_exceptions(self) -> None:
        registry = MetricsRegistry()

        registry.start_request(method="GET", path="/health")
        registry.finish_request(
            method="GET",
            path="/health",
            status_code=200,
            duration_ms=10.5,
            had_exception=False,
        )
        registry.start_request(method="POST", path="/api/v1/ask")
        registry.finish_request(
            method="POST",
            path="/api/v1/ask",
            status_code=500,
            duration_ms=25.0,
            had_exception=True,
        )

        snapshot = registry.snapshot()

        self.assertEqual(snapshot["total_requests"], 2)
        self.assertEqual(snapshot["in_flight_requests"], 0)
        self.assertEqual(snapshot["total_exceptions"], 1)
        self.assertEqual(len(snapshot["paths"]), 2)

        ask_metrics = next(item for item in snapshot["paths"] if item["path"] == "/api/v1/ask")
        self.assertEqual(ask_metrics["status_counts"], {"500": 1})
        self.assertEqual(ask_metrics["requests"], 1)

    def test_render_prometheus_exposes_metrics_text(self) -> None:
        registry = MetricsRegistry()

        registry.start_request(method="GET", path="/health")
        registry.finish_request(
            method="GET",
            path="/health",
            status_code=200,
            duration_ms=5.0,
            had_exception=False,
        )

        rendered = registry.render_prometheus().decode("utf-8")

        self.assertIn("kg_http_requests_started_total", rendered)
        self.assertIn('path="/health"', rendered)

    def test_render_prometheus_includes_service_level_observability_metrics(self) -> None:
        registry = MetricsRegistry()

        registry.record_qa_request(outcome="success")
        registry.record_qa_request(outcome="rejected")
        registry.record_neo4j_query(outcome="success", duration_ms=12.5, row_count=4)
        registry.record_neo4j_query(outcome="error", duration_ms=8.0)
        registry.record_ollama_request(
            model="llama3.2",
            format_name="json",
            outcome="success",
            duration_ms=250.0,
        )

        rendered = registry.render_prometheus().decode("utf-8")

        self.assertIn("kg_qa_requests_total", rendered)
        self.assertIn('outcome="rejected"', rendered)
        self.assertIn("kg_neo4j_queries_total", rendered)
        self.assertIn("kg_neo4j_query_duration_seconds", rendered)
        self.assertIn("kg_neo4j_rows_returned", rendered)
        self.assertIn("kg_ollama_requests_total", rendered)
        self.assertIn('model="llama3.2"', rendered)


if __name__ == "__main__":
    unittest.main()