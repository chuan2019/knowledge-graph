from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.core.middleware import MetricsRegistry


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class OllamaClient:
    def __init__(self, settings: Settings, metrics_registry: MetricsRegistry | None = None) -> None:
        self._settings = settings
        self._metrics_registry = metrics_registry
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
            limits=httpx.Limits(
                max_connections=settings.ollama_max_connections,
                max_keepalive_connections=settings.ollama_max_keepalive_connections,
            ),
        )

    async def close(self) -> None:
        logger.debug("Closing Ollama HTTP client")
        await self._client.aclose()

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        response_text = await self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            format_name="json",
            temperature=temperature,
        )
        return json.loads(response_text)

    async def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        return await self._generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            format_name=None,
            temperature=temperature,
        )

    async def _generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None,
        format_name: str | None,
        temperature: float | None,
    ) -> str:
        with tracer.start_as_current_span("ollama.generate") as span:
            model_name = model or self._settings.ollama_model
            response_format = format_name or "text"
            span.set_attribute("llm.system", "ollama")
            span.set_attribute("llm.model", model_name)
            span.set_attribute("llm.format", response_format)
            span.set_attribute("llm.prompt_length", len(user_prompt))
            payload: dict[str, Any] = {
                "model": model_name,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": {
                    "temperature": (
                        self._settings.answer_temperature
                        if temperature is None
                        else temperature
                    )
                },
            }
            if format_name is not None:
                payload["format"] = format_name

            logger.debug(
                "Calling Ollama generate API: model=%s format=%s prompt_length=%s",
                model_name,
                response_format,
                len(user_prompt),
            )
            start = time.perf_counter()

            try:
                response = await self._client.post("/api/generate", json=payload)
            except httpx.PoolTimeout as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                if self._metrics_registry is not None:
                    self._metrics_registry.record_ollama_request(
                        model=model_name,
                        format_name=response_format,
                        outcome="pool_timeout",
                        duration_ms=duration_ms,
                    )
                logger.warning(
                    "Ollama connection pool exhausted: model=%s max_connections=%s",
                    model_name,
                    self._settings.ollama_max_connections,
                )
                raise ServiceUnavailableError(
                    "Ollama",
                    detail=(
                        "Ollama connection pool is exhausted. "
                        "Increase pool capacity or reduce request concurrency."
                    ),
                ) from exc
            except httpx.TimeoutException as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                if self._metrics_registry is not None:
                    self._metrics_registry.record_ollama_request(
                        model=model_name,
                        format_name=response_format,
                        outcome="timeout",
                        duration_ms=duration_ms,
                    )
                logger.warning(
                    "Ollama request timed out: model=%s timeout_seconds=%.2f",
                    model_name,
                    self._settings.ollama_timeout_seconds,
                )
                raise ServiceUnavailableError(
                    "Ollama",
                    detail=(
                        "Ollama request timed out under current load. "
                        "Retry the request or scale the model-serving tier."
                    ),
                ) from exc

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                detail = self._extract_error_detail(response)
                requested_model = str(payload["model"])
                span.set_attribute("llm.http_status_code", response.status_code)
                if self._metrics_registry is not None:
                    self._metrics_registry.record_ollama_request(
                        model=model_name,
                        format_name=response_format,
                        outcome=f"http_{response.status_code}",
                        duration_ms=duration_ms,
                    )
                logger.warning(
                    "Ollama request failed: status=%s model=%s detail=%s",
                    response.status_code,
                    requested_model,
                    detail,
                )
                if response.status_code == 404 and requested_model in detail:
                    raise ServiceUnavailableError(
                        "Ollama",
                        detail=(
                            f"Model '{requested_model}' is not available in Ollama. "
                            f"Pull it first with: ollama pull {requested_model}"
                        ),
                    ) from exc

                raise ServiceUnavailableError(
                    "Ollama",
                    detail=detail or f"HTTP {response.status_code} returned from Ollama",
                ) from exc

            data = response.json()
            content = data.get("response")
            if not isinstance(content, str) or not content.strip():
                duration_ms = (time.perf_counter() - start) * 1000
                if self._metrics_registry is not None:
                    self._metrics_registry.record_ollama_request(
                        model=model_name,
                        format_name=response_format,
                        outcome="empty_response",
                        duration_ms=duration_ms,
                    )
                logger.warning("Ollama returned an empty response body for model=%s", model_name)
                raise ValueError("Ollama returned an empty response.")
            duration_ms = (time.perf_counter() - start) * 1000
            if self._metrics_registry is not None:
                self._metrics_registry.record_ollama_request(
                    model=model_name,
                    format_name=response_format,
                    outcome="success",
                    duration_ms=duration_ms,
                )
            span.set_attribute("llm.response_length", len(content.strip()))
            logger.debug(
                "Ollama request succeeded: model=%s response_length=%s duration_ms=%.3f",
                model_name,
                len(content.strip()),
                duration_ms,
            )
            return content.strip()

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip()

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, str):
                return error

        return response.text.strip()
