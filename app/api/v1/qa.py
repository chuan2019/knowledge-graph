"""Graph QA endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.models.qa import AskRequest, AskResponse, SchemaResponse
from app.services.qa_service import GRAPH_SCHEMA, GraphQAService

router = APIRouter()
legacy_router = APIRouter(include_in_schema=False)
logger = logging.getLogger(__name__)


async def _ask_question(payload: AskRequest, request: Request) -> AskResponse:
    logger.debug(
        "Received ask request: path=%s model=%s include_rows=%s question_length=%s",
        request.url.path,
        payload.model or "default",
        payload.include_rows,
        len(payload.question),
    )
    qa_service: GraphQAService = request.app.state.qa_service
    answer, cypher, rows, agent_trace = await qa_service.answer_question(
        payload.question,
        model=payload.model,
    )
    logger.debug(
        "Ask request completed: path=%s row_count=%s cypher_length=%s",
        request.url.path,
        len(rows),
        len(cypher),
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
    logger.debug("Schema requested via versioned route")
    return _schema_response()


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest, request: Request) -> AskResponse:
    return await _ask_question(payload, request)


@legacy_router.get("/schema")
async def legacy_schema() -> SchemaResponse:
    logger.debug("Schema requested via legacy route")
    return _schema_response()


@legacy_router.post("/api/ask")
async def legacy_ask_question(payload: AskRequest, request: Request) -> AskResponse:
    return await _ask_question(payload, request)
