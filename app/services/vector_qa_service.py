"""Vector-based RAG QA service using Weaviate for semantic retrieval."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from opentelemetry import trace

from app.core.config import Settings
from app.core.errors import TooManyRequestsError
from app.core.middleware import MetricsRegistry
from app.services.ollama_client import OllamaClient
from app.services.vector_store import VectorStore

VECTOR_ANSWER_SYSTEM_PROMPT = """
You answer questions about media content using only the retrieved documents from a vector similarity search.
Each document describes a title (film, TV series, documentary, etc.) with its synopsis, genre, type, studio, and release year.
Similarity scores (_certainty) indicate how closely each document matches the query — higher is more relevant.
Synthesise a helpful, grounded answer from the provided documents.
If the documents do not contain enough information to answer the question, say so clearly.
Be concise and factual.
""".strip()

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class VectorQAService:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        ollama_client: OllamaClient,
        metrics_registry: MetricsRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store
        self._ollama_client = ollama_client
        self._metrics_registry = metrics_registry
        self._request_semaphore = asyncio.Semaphore(settings.qa_max_concurrency)

    async def answer_question(
        self,
        question: str,
        *,
        model: str | None = None,
        limit: int = 10,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        with tracer.start_as_current_span("vector_qa.answer_question") as span:
            span.set_attribute("vqa.model", model or self._settings.ollama_model)
            span.set_attribute("vqa.question_length", len(question))
            span.set_attribute("vqa.limit", limit)
            logger.debug(
                "Vector QA: model=%s question_length=%s limit=%s",
                model or self._settings.ollama_model,
                len(question),
                limit,
            )

            async with self._acquire_request_slot(question=question):
                agent_trace = ["Received user question."]

                agent_trace.append(f"Running semantic search (limit={limit}).")
                hits = await self._vector_store.semantic_search(question, limit=limit)
                span.set_attribute("vqa.hit_count", len(hits))
                agent_trace.append(f"Retrieved {len(hits)} semantically similar documents.")
                logger.debug("Semantic search returned %s hits", len(hits))

                answer = await self._synthesize_answer(
                    question=question,
                    hits=hits,
                    model=model,
                )
                agent_trace.append("Synthesized natural-language answer from retrieved documents.")
                logger.debug("Vector QA answer synthesis completed")

                if self._metrics_registry is not None:
                    self._metrics_registry.record_qa_request(outcome="success")

                return answer, hits, agent_trace

    @asynccontextmanager
    async def _acquire_request_slot(self, *, question: str):
        queue_timeout_seconds = self._settings.qa_queue_timeout_ms / 1000
        try:
            await asyncio.wait_for(
                self._request_semaphore.acquire(),
                timeout=queue_timeout_seconds,
            )
        except TimeoutError as exc:
            logger.warning(
                "Rejected vector QA question due to saturated capacity: question_length=%s",
                len(question),
            )
            if self._metrics_registry is not None:
                self._metrics_registry.record_qa_request(outcome="rejected")
            raise TooManyRequestsError(
                detail="The QA service is saturated. Retry shortly."
            ) from exc

        try:
            yield
        finally:
            self._request_semaphore.release()

    async def _synthesize_answer(
        self,
        *,
        question: str,
        hits: list[dict[str, Any]],
        model: str | None,
    ) -> str:
        with tracer.start_as_current_span("vector_qa.synthesize_answer") as span:
            if not hits:
                span.set_attribute("vqa.hit_count", 0)
                return "No semantically similar content was found in the vector store for that question."

            limited = hits[: self._settings.result_row_limit]
            span.set_attribute("vqa.hit_count", len(limited))
            logger.debug("Synthesizing answer from %s vector hits", len(limited))

            context_prompt = (
                f"Question:\n{question}\n\n"
                f"Retrieved documents (JSON, ordered by similarity):\n"
                f"{json.dumps(limited, default=str, indent=2)}\n\n"
                "Answer the question based on the retrieved documents. "
                "Mention relevant titles by name and note their genre, type, or synopsis where useful."
            )
            return await self._ollama_client.generate_text(
                system_prompt=VECTOR_ANSWER_SYSTEM_PROMPT,
                user_prompt=context_prompt,
                model=model,
                temperature=self._settings.answer_temperature,
            )
