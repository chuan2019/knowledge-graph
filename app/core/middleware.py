"""Middleware for request timing and in-memory metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import threading
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


@dataclass
class PathMetricBucket:
    requests: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    status_counts: defaultdict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )


class MetricsRegistry:
    """Stores in-memory request metrics for the FastAPI app."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests = 0
        self._in_flight_requests = 0
        self._total_exceptions = 0
        self._path_metrics: dict[tuple[str, str], PathMetricBucket] = defaultdict(
            PathMetricBucket
        )

    def start_request(self) -> None:
        with self._lock:
            self._total_requests += 1
            self._in_flight_requests += 1

    def finish_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        had_exception: bool,
    ) -> None:
        with self._lock:
            self._in_flight_requests -= 1
            if had_exception:
                self._total_exceptions += 1

            metric = self._path_metrics[(method, path)]
            metric.requests += 1
            metric.total_duration_ms += duration_ms
            metric.max_duration_ms = max(metric.max_duration_ms, duration_ms)
            metric.status_counts[str(status_code)] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            paths: list[dict[str, object]] = []
            for (method, path), metric in sorted(self._path_metrics.items()):
                requests = metric.requests
                total_duration_ms = metric.total_duration_ms
                max_duration_ms = metric.max_duration_ms
                avg_duration_ms = total_duration_ms / requests if requests else 0.0
                paths.append(
                    {
                        "method": method,
                        "path": path,
                        "requests": requests,
                        "avg_duration_ms": round(avg_duration_ms, 3),
                        "max_duration_ms": round(max_duration_ms, 3),
                        "status_counts": dict(metric.status_counts),
                    }
                )

            return {
                "total_requests": self._total_requests,
                "in_flight_requests": self._in_flight_requests,
                "total_exceptions": self._total_exceptions,
                "paths": paths,
            }


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects request counts and timings in an in-memory registry."""

    def __init__(self, app, registry: MetricsRegistry):
        super().__init__(app)
        self._registry = registry

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        self._registry.start_request()
        status_code = 500
        had_exception = False
        logger.debug("Request started: %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            had_exception = True
            logger.exception(
                "Request failed before response: %s %s",
                request.method,
                request.url.path,
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Response-Time"] = f"{duration_ms:.3f}ms"
            logger.debug(
                "Request completed: %s %s status=%s duration_ms=%.3f",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._registry.finish_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                had_exception=had_exception,
            )
