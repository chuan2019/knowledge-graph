"""Graph QA endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.qa import AskRequest, AskResponse, SchemaResponse
from app.services.qa_service import GRAPH_SCHEMA, GraphQAService

router = APIRouter()
legacy_router = APIRouter(include_in_schema=False)


async def _ask_question(payload: AskRequest, request: Request) -> AskResponse:
    qa_service: GraphQAService = request.app.state.qa_service
    answer, cypher, rows, agent_trace = await qa_service.answer_question(
        payload.question,
        model=payload.model,
    )
    return AskResponse(
        question=payload.question,
        answer=answer,
        cypher=cypher,
        rows=rows if payload.include_rows else [],
        row_count=len(rows),
        agent_trace=agent_trace,
    )


def _schema_response() -> SchemaResponse:
    return SchemaResponse(graph_schema=GRAPH_SCHEMA)


@router.get("/schema", response_model=SchemaResponse)
async def schema() -> SchemaResponse:
    return _schema_response()


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest, request: Request) -> AskResponse:
    return await _ask_question(payload, request)


@legacy_router.get("/schema")
async def legacy_schema() -> SchemaResponse:
    return _schema_response()


@legacy_router.post("/api/ask")
async def legacy_ask_question(payload: AskRequest, request: Request) -> AskResponse:
    return await _ask_question(payload, request)
