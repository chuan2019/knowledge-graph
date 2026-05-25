from __future__ import annotations

import unittest

from app.core.middleware import MetricsRegistry


class MetricsRegistryUnitTestCase(unittest.TestCase):
    def test_snapshot_tracks_requests_status_and_exceptions(self) -> None:
        registry = MetricsRegistry()

        registry.start_request()
        registry.finish_request(
            method="GET",
            path="/health",
            status_code=200,
            duration_ms=10.5,
            had_exception=False,
        )
        registry.start_request()
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


if __name__ == "__main__":
    unittest.main()