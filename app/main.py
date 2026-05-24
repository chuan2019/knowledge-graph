from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.schemas import AskRequest, AskResponse, HealthResponse, SchemaResponse
from app.services.graph_store import GraphStore
from app.services.ollama_client import OllamaClient
from app.services.qa_service import GRAPH_SCHEMA, GraphQAService

STATIC_DIR = Path(__file__).with_name("static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    graph_store = GraphStore(settings)
    graph_store.verify_connectivity()
    ollama_client = OllamaClient(settings)
    qa_service = GraphQAService(settings, graph_store, ollama_client)

    app.state.settings = settings
    app.state.graph_store = graph_store
    app.state.ollama_client = ollama_client
    app.state.qa_service = qa_service

    try:
        yield
    finally:
        graph_store.close()
        await ollama_client.close()


app = FastAPI(
    title="Knowledge Graph QA Service",
    version="0.1.0",
    description=(
        "FastAPI service for graph-backed question answering over the KG-RAG demo dataset."
    ),
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = app.state.settings
    return HealthResponse(
        status="ok",
        neo4j=settings.neo4j_uri,
        ollama_base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )


@app.get("/schema", response_model=SchemaResponse)
async def schema() -> SchemaResponse:
    return SchemaResponse(graph_schema=GRAPH_SCHEMA)


@app.post("/api/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    try:
        answer, cypher, rows, agent_trace = await app.state.qa_service.answer_question(
            payload.question,
            model=payload.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AskResponse(
        question=payload.question,
        answer=answer,
        cypher=cypher,
        rows=rows if payload.include_rows else [],
        row_count=len(rows),
        agent_trace=agent_trace,
    )