from __future__ import annotations

from dataclasses import dataclass
import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TracingManager:
    tracer_provider: TracerProvider
    fastapi_instrumented: bool = False
    httpx_instrumented: bool = False


def setup_tracing(app: FastAPI, settings: Settings) -> TracingManager | None:
    if not settings.tracing_enabled:
        logger.info("Distributed tracing is disabled")
        return None

    resource = Resource.create({"service.name": settings.tracing_service_name})
    tracer_provider = TracerProvider(resource=resource)
    span_exporter = OTLPSpanExporter(endpoint=settings.otlp_traces_exporter_endpoint)
    span_processor = BatchSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)

    logger.info(
        "Distributed tracing enabled: service_name=%s exporter=%s",
        settings.tracing_service_name,
        settings.otlp_traces_exporter_endpoint,
    )
    return TracingManager(
        tracer_provider=tracer_provider,
        fastapi_instrumented=True,
        httpx_instrumented=True,
    )


def shutdown_tracing(app: FastAPI, manager: TracingManager | None) -> None:
    if manager is None:
        return

    if manager.fastapi_instrumented:
        FastAPIInstrumentor.uninstrument_app(app)

    if manager.httpx_instrumented:
        HTTPXClientInstrumentor().uninstrument()

    manager.tracer_provider.force_flush()
    manager.tracer_provider.shutdown()
    logger.info("Distributed tracing shut down cleanly")


def current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None

    return format(span_context.trace_id, "032x")


def current_span_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None

    return format(span_context.span_id, "016x")