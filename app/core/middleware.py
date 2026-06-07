"""Middleware for request timing and in-memory metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import threading
import time
from collections import defaultdict

from fastapi import Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.tracing import current_span_id, current_trace_id


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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
        self._prometheus_registry = CollectorRegistry()
        self._requests_started = Counter(
            "kg_http_requests_started_total",
            "Total HTTP requests started.",
            labelnames=("method", "path"),
            registry=self._prometheus_registry,
        )
        self._requests_completed = Counter(
            "kg_http_requests_completed_total",
            "Total HTTP requests completed.",
            labelnames=("method", "path", "status_code"),
            registry=self._prometheus_registry,
        )
        self._request_duration = Histogram(
            "kg_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            labelnames=("method", "path"),
            registry=self._prometheus_registry,
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
        )
        self._in_flight = Gauge(
            "kg_http_requests_in_flight",
            "Current number of in-flight HTTP requests.",
            registry=self._prometheus_registry,
        )
        self._exceptions_total = Counter(
            "kg_http_request_exceptions_total",
            "Total HTTP requests ending with an exception before a normal response.",
            labelnames=("method", "path"),
            registry=self._prometheus_registry,
        )
        self._qa_requests_total = Counter(
            "kg_qa_requests_total",
            "Total QA requests by outcome.",
            labelnames=("outcome",),
            registry=self._prometheus_registry,
        )
        self._neo4j_queries_total = Counter(
            "kg_neo4j_queries_total",
            "Total Neo4j read queries by outcome.",
            labelnames=("outcome",),
            registry=self._prometheus_registry,
        )
        self._neo4j_query_duration = Histogram(
            "kg_neo4j_query_duration_seconds",
            "Neo4j read query duration in seconds.",
            labelnames=("outcome",),
            registry=self._prometheus_registry,
            buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
        )
        self._neo4j_rows = Histogram(
            "kg_neo4j_rows_returned",
            "Neo4j rows returned per read query.",
            registry=self._prometheus_registry,
            buckets=(0, 1, 5, 10, 25, 50, 100, 250, float("inf")),
        )
        self._ollama_requests_total = Counter(
            "kg_ollama_requests_total",
            "Total Ollama generate requests by model, format, and outcome.",
            labelnames=("model", "format", "outcome"),
            registry=self._prometheus_registry,
        )
        self._ollama_request_duration = Histogram(
            "kg_ollama_request_duration_seconds",
            "Ollama generate request duration in seconds.",
            labelnames=("model", "format", "outcome"),
            registry=self._prometheus_registry,
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
        )

    def start_request(self, *, method: str, path: str) -> None:
        with self._lock:
            self._total_requests += 1
            self._in_flight_requests += 1
        self._requests_started.labels(method=method, path=path).inc()
        self._in_flight.inc()

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

        self._requests_completed.labels(
            method=method,
            path=path,
            status_code=str(status_code),
        ).inc()
        self._request_duration.labels(method=method, path=path).observe(
            duration_ms / 1000
        )
        self._in_flight.dec()
        if had_exception:
            self._exceptions_total.labels(method=method, path=path).inc()

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

    def render_prometheus(self) -> bytes:
        return generate_latest(self._prometheus_registry)

    def record_qa_request(self, *, outcome: str) -> None:
        self._qa_requests_total.labels(outcome=outcome).inc()

    def record_neo4j_query(self, *, outcome: str, duration_ms: float, row_count: int = 0) -> None:
        self._neo4j_queries_total.labels(outcome=outcome).inc()
        self._neo4j_query_duration.labels(outcome=outcome).observe(duration_ms / 1000)
        if outcome == "success":
            self._neo4j_rows.observe(row_count)

    def record_ollama_request(
        self,
        *,
        model: str,
        format_name: str,
        outcome: str,
        duration_ms: float,
    ) -> None:
        self._ollama_requests_total.labels(
            model=model,
            format=format_name,
            outcome=outcome,
        ).inc()
        self._ollama_request_duration.labels(
            model=model,
            format=format_name,
            outcome=outcome,
        ).observe(duration_ms / 1000)

    @property
    def prometheus_content_type(self) -> str:
        return CONTENT_TYPE_LATEST


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects request counts and timings in an in-memory registry."""

    def __init__(self, app, registry: MetricsRegistry):
        super().__init__(app)
        self._registry = registry

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        self._registry.start_request(method=request.method, path=request.url.path)
        status_code = 500
        had_exception = False
        logger.debug("Request started: %s %s", request.method, request.url.path)

        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("url.path", request.url.path)

            # Stash trace context in request.state before call_next so that error
            # handlers called outside this span (by ServerErrorMiddleware) can still
            # access the IDs.
            request.state.trace_id = current_trace_id()
            request.state.span_id = current_span_id()

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
                trace_id = current_trace_id()
                if trace_id is not None:
                    response.headers["X-Trace-Id"] = trace_id
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
