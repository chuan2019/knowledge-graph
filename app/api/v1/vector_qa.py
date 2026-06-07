"""Vector QA endpoints — semantic search via Weaviate."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.vector_qa import VectorAskRequest, VectorAskResponse
from app.services.vector_qa_service import VectorQAService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/vector-ask", response_model=VectorAskResponse)
async def vector_ask_question(payload: VectorAskRequest, request: Request) -> VectorAskResponse:
    vector_qa_service: VectorQAService | None = getattr(request.app.state, "vector_qa_service", None)
    if vector_qa_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Vector QA service is not available. "
                "Ensure Weaviate is running and the ContentTitle collection has been loaded "
                "via kg4rag/vector-data-loader.py."
            ),
        )

    logger.info(
        "Received vector-ask request: model=%s limit=%s question_length=%s",
        payload.model or "default",
        payload.limit,
        len(payload.question),
    )

    answer, hits, agent_trace = await vector_qa_service.answer_question(
        payload.question,
        model=payload.model,
        limit=payload.limit,
    )

    logger.info(
        "Vector-ask completed: hit_count=%s",
        len(hits),
    )
    return VectorAskResponse(
        question=payload.question,
        answer=answer,
        hits=hits,
        hit_count=len(hits),
        agent_trace=agent_trace,
    )
