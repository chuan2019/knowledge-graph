from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import ui as ui_router
from app.api.v1 import metrics as metrics_router
from app.api.v1 import qa as qa_router
from app.api.v1 import services as services_router
from app.core.config import Settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import MetricsMiddleware, MetricsRegistry
from app.core.tracing import setup_tracing, shutdown_tracing
from app.models.qa import HealthResponse
from app.services.graph_store import GraphStore
from app.services.ollama_client import OllamaClient
from app.services.qa_service import GraphQAService

STATIC_DIR = Path(__file__).with_name("static")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    tracing_manager = setup_tracing(app, settings)
    logger.info(
        "Starting Knowledge Graph QA Service with Neo4j=%s Ollama=%s model=%s log_level=%s tracing_enabled=%s",
        settings.neo4j_uri,
        settings.ollama_base_url,
        settings.ollama_model,
        settings.log_level.upper(),
        settings.tracing_enabled,
    )
    metrics_registry = app.state.metrics_registry
    graph_store = GraphStore(settings, metrics_registry=metrics_registry)
    logger.debug("Verifying Neo4j connectivity")
    await graph_store.verify_connectivity()
    ollama_client = OllamaClient(settings, metrics_registry=metrics_registry)
    qa_service = GraphQAService(
        settings,
        graph_store,
        ollama_client,
        metrics_registry=metrics_registry,
    )

    app.state.settings = settings
    app.state.graph_store = graph_store
    app.state.ollama_client = ollama_client
    app.state.qa_service = qa_service
    app.state.tracing_manager = tracing_manager
    logger.info("Application services initialized successfully")

    try:
        yield
    finally:
        logger.info("Shutting down Knowledge Graph QA Service")
        shutdown_tracing(app, tracing_manager)
        await graph_store.close()
        await ollama_client.close()
        logger.info("Application services shut down cleanly")


app = FastAPI(
    title="Knowledge Graph QA Service",
    version="0.1.0",
    description=(
        "FastAPI service for graph-backed question answering over the KG-RAG demo dataset."
    ),
    lifespan=lifespan,
)

metrics_registry = MetricsRegistry()
app.state.metrics_registry = metrics_registry
app.add_middleware(MetricsMiddleware, registry=metrics_registry)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
register_error_handlers(app)
app.include_router(ui_router.router)
app.include_router(metrics_router.router, prefix="/api/v1")
app.include_router(qa_router.router, prefix="/api/v1")
app.include_router(services_router.router, prefix="/api/v1")
app.include_router(metrics_router.legacy_router)
app.include_router(qa_router.legacy_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = app.state.settings
    logger.debug("Health check requested")
    return HealthResponse(
        status="ok",
        neo4j=settings.neo4j_uri,
        ollama_base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )