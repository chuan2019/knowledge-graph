from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from neo4j.exceptions import CypherSyntaxError, Neo4jError
from opentelemetry import trace

from app.core.config import Settings
from app.core.errors import TooManyRequestsError
from app.core.middleware import MetricsRegistry
from app.services.graph_store import GraphStore
from app.services.ollama_client import OllamaClient

GRAPH_SCHEMA = """
Nodes and key properties:
- Title(title_id, title_name, title_type, genre, studio, release_year, duration_minutes, season_count, created_at)
- Version(version_id, title_id, version_type, resolution, frame_rate, audio_channels, hdr_format, file_size_gb, is_localized, created_date)
- Client(client_id, client_name, client_type, tier, region_focus, active_since, credit_limit_usd, status)
- Region(region_id, region_name, continent)
- Language(language_code, language_name, language_family)
- DeliveryPoint(delivery_point_id, point_name, delivery_type, region_id)
- Rights(rights_id, version_id, client_id, region_id, rights_type, start_date, end_date, is_active, territorial_restrictions, exclusivity_window_days)
- LocalizationJob(job_id, version_id, language_code, job_type, status, completion_date, quality_score, vendor)
- DeliverySpec(spec_id, delivery_point_id, version_id, required_resolution, required_audio, required_hdr, required_container, max_bitrate_mbps, is_mandatory)
- DeliveryRequest(request_id, version_id, client_id, delivery_point_id, request_date, deadline, status, actual_completion, priority, file_size_gb)

Relationships:
- (Title)-[:HAS_VERSION]->(Version)
- (DeliveryPoint)-[:LOCATED_IN]->(Region)
- (Rights)-[:FOR_VERSION]->(Version)
- (Rights)-[:GRANTED_TO]->(Client)
- (Rights)-[:FOR_REGION]->(Region)
- (LocalizationJob)-[:FOR_VERSION]->(Version)
- (LocalizationJob)-[:LOCALIZED_FOR]->(Language)
- (DeliverySpec)-[:FOR_DELIVERY_POINT]->(DeliveryPoint)
- (DeliverySpec)-[:FOR_VERSION]->(Version)
- (DeliveryRequest)-[:FOR_VERSION]->(Version)
- (DeliveryRequest)-[:REQUESTED_BY]->(Client)
- (DeliveryRequest)-[:TO_POINT]->(DeliveryPoint)
""".strip()

EXAMPLE_QUERIES = """
Example 1:
MATCH (t:Title)-[:HAS_VERSION]->(v:Version)
MATCH (rg:Rights)-[:FOR_VERSION]->(v)
MATCH (rg)-[:GRANTED_TO]->(c:Client)
MATCH (rg)-[:FOR_REGION]->(r:Region)
WHERE rg.is_active = true AND v.is_localized = true AND c.tier = 'Tier 1'
RETURN t.title_name, v.version_id, c.client_name, r.region_name, rg.rights_type, rg.end_date
LIMIT 20

Example 2:
MATCH (dr:DeliveryRequest)-[:FOR_VERSION]->(v:Version)
MATCH (dr)-[:REQUESTED_BY]->(c:Client)
MATCH (dr)-[:TO_POINT]->(dp:DeliveryPoint)-[:LOCATED_IN]->(r:Region)
MATCH (t:Title)-[:HAS_VERSION]->(v)
WHERE dr.status IN ['Delayed', 'Failed']
RETURN t.title_name, v.version_id, c.client_name, dp.point_name, r.region_name, dr.status, dr.deadline
ORDER BY dr.deadline ASC
LIMIT 20
""".strip()

PLANNER_SYSTEM_PROMPT = """
You translate user questions into safe, read-only Cypher for Neo4j.
Return valid JSON with keys: cypher, rationale.
Rules:
- Use only the provided schema.
- Generate read-only Cypher only.
- Never use CREATE, MERGE, DELETE, DETACH, SET, REMOVE, DROP, LOAD CSV, or admin procedures.
- Always include a RETURN clause.
- Prefer explicit MATCH patterns.
- For existence checks, use `EXISTS { MATCH ... }`, not `EXISTS((...))` pattern expressions.
- Keep results concise and useful for answer synthesis.
""".strip()

ANSWER_SYSTEM_PROMPT = """
You answer questions using only the retrieved graph records.
If the retrieved records do not fully support an answer, say what is missing.
Be concise, factual, and avoid inventing entities or counts.
""".strip()

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class GraphQAService:
    def __init__(
        self,
        settings: Settings,
        graph_store: GraphStore,
        ollama_client: OllamaClient,
        metrics_registry: MetricsRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._graph_store = graph_store
        self._ollama_client = ollama_client
        self._metrics_registry = metrics_registry
        self._request_semaphore = asyncio.Semaphore(settings.qa_max_concurrency)

    async def answer_question(
        self,
        question: str,
        *,
        model: str | None = None,
    ) -> tuple[str, str, list[dict[str, Any]], list[str]]:
        with tracer.start_as_current_span("qa.answer_question") as span:
            span.set_attribute("qa.model", model or self._settings.ollama_model)
            span.set_attribute("qa.question_length", len(question))
            span.set_attribute("qa.max_retries", self._settings.max_query_retries)
            logger.debug(
                "Answering question: model=%s question_length=%s max_retries=%s",
                model or self._settings.ollama_model,
                len(question),
                self._settings.max_query_retries,
            )
            async with self._acquire_request_slot(question=question):
                agent_trace = ["Received user question."]
                last_error: str | None = None
                last_query: str | None = None

                for attempt in range(1, self._settings.max_query_retries + 2):
                    span.set_attribute("qa.attempt", attempt)
                    logger.debug("Planning Cypher attempt %s", attempt)
                    cypher = await self._plan_cypher(
                        question=question,
                        model=model,
                        error_feedback=last_error,
                        previous_query=last_query,
                    )
                    agent_trace.append(f"Planned Cypher on attempt {attempt}.")
                    logger.debug("Planner produced Cypher on attempt %s: %s", attempt, cypher)
                    try:
                        rows = await self._graph_store.run_read_query(cypher)
                        agent_trace.append(f"Executed Cypher and retrieved {len(rows)} rows.")
                        span.set_attribute("qa.row_count", len(rows))
                        logger.debug(
                            "Cypher execution succeeded on attempt %s with %s rows",
                            attempt,
                            len(rows),
                        )
                        answer = await self._summarize_answer(
                            question=question,
                            cypher=cypher,
                            rows=rows,
                            model=model,
                        )
                        agent_trace.append("Synthesized natural-language answer.")
                        logger.debug("Answer synthesis completed on attempt %s", attempt)
                        if self._metrics_registry is not None:
                            self._metrics_registry.record_qa_request(outcome="success")
                        return answer, cypher, rows, agent_trace
                    except (ValueError, CypherSyntaxError, Neo4jError) as exc:
                        last_error = str(exc)
                        last_query = cypher
                        span.set_attribute("qa.last_error", last_error)
                        logger.warning(
                            "Cypher execution failed on attempt %s: %s",
                            attempt,
                            last_error,
                        )
                        agent_trace.append(
                            f"Cypher execution failed on attempt {attempt}: {last_error}"
                        )

                logger.error("Exhausted Cypher retries: %s", last_error)
                if self._metrics_registry is not None:
                    self._metrics_registry.record_qa_request(outcome="error")
                raise RuntimeError(f"Unable to answer question after retries: {last_error}")

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
                "Rejected question due to saturated request capacity: question_length=%s max_concurrency=%s queue_timeout_ms=%s",
                len(question),
                self._settings.qa_max_concurrency,
                self._settings.qa_queue_timeout_ms,
            )
            if self._metrics_registry is not None:
                self._metrics_registry.record_qa_request(outcome="rejected")
            raise TooManyRequestsError(
                detail=(
                    "The QA service is saturated under current load. "
                    "Retry shortly or scale the API and model-serving tiers."
                )
            ) from exc

        try:
            logger.debug("Acquired QA request slot")
            yield
        finally:
            self._request_semaphore.release()
            logger.debug("Released QA request slot")

    async def _plan_cypher(
        self,
        *,
        question: str,
        model: str | None,
        error_feedback: str | None,
        previous_query: str | None,
    ) -> str:
        with tracer.start_as_current_span("qa.plan_cypher") as span:
            feedback = ""
            if error_feedback and previous_query:
                feedback = (
                    "\nPrevious query failed. Repair it instead of starting over.\n"
                    f"Previous query:\n{previous_query}\n"
                    f"Neo4j error:\n{error_feedback}\n"
                )

            planner_prompt = (
                f"Schema:\n{GRAPH_SCHEMA}\n\n"
                f"Examples:\n{EXAMPLE_QUERIES}\n\n"
                f"Question:\n{question}\n"
                f"{feedback}\n"
                "Return JSON only."
            )
            span.set_attribute("qa.model", model or self._settings.ollama_model)
            span.set_attribute("qa.feedback_present", bool(feedback))
            logger.debug(
                "Sending planner request to Ollama: model=%s feedback_present=%s",
                model or self._settings.ollama_model,
                bool(feedback),
            )
            plan = await self._ollama_client.generate_json(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_prompt=planner_prompt,
                model=model,
                temperature=self._settings.planner_temperature,
            )
            cypher = plan.get("cypher")
            if not isinstance(cypher, str) or not cypher.strip():
                raise ValueError(f"Planner did not return a usable Cypher query: {json.dumps(plan)}")
            span.set_attribute("qa.cypher_length", len(cypher.strip()))
            logger.debug("Planner response contained a usable Cypher query")
            return cypher.strip()

    async def _summarize_answer(
        self,
        *,
        question: str,
        cypher: str,
        rows: list[dict[str, Any]],
        model: str | None,
    ) -> str:
        with tracer.start_as_current_span("qa.summarize_answer") as span:
            if not rows:
                logger.debug("No rows returned for question; skipping answer synthesis")
                span.set_attribute("qa.row_count", 0)
                return "I could not find matching records in the graph for that question."

            limited_rows = rows[: self._settings.result_row_limit]
            span.set_attribute("qa.row_count", len(limited_rows))
            logger.debug(
                "Sending answer synthesis request to Ollama with %s row(s)",
                len(limited_rows),
            )
            answer_prompt = (
                f"Question:\n{question}\n\n"
                f"Cypher used:\n{cypher}\n\n"
                f"Retrieved rows (JSON):\n{json.dumps(limited_rows, default=str, indent=2)}\n\n"
                "Answer the question in natural language. Mention important filters or uncertainty when relevant."
            )
            return await self._ollama_client.generate_text(
                system_prompt=ANSWER_SYSTEM_PROMPT,
                user_prompt=answer_prompt,
                model=model,
                temperature=self._settings.answer_temperature,
            )
