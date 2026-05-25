from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.errors import ServiceUnavailableError


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=60.0)

    async def close(self) -> None:
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
        payload: dict[str, Any] = {
            "model": model or self._settings.ollama_model,
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

        response = await self._client.post("/api/generate", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_error_detail(response)
            requested_model = str(payload["model"])
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
            raise ValueError("Ollama returned an empty response.")
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
