from __future__ import annotations

import unittest

import httpx

from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.services.ollama_client import OllamaClient


class OllamaClientUnitTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = OllamaClient(Settings())

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_generate_text_raises_clear_error_when_model_missing(self) -> None:
        request = httpx.Request("POST", "http://ollama:11434/api/generate")
        response = httpx.Response(
            404,
            request=request,
            json={"error": "model 'llama3.2' not found"},
        )

        async def fake_post(*_args, **_kwargs):
            return response

        self.client._client.post = fake_post  # type: ignore[method-assign]

        with self.assertRaises(ServiceUnavailableError) as context:
            await self.client.generate_text(
                system_prompt="system",
                user_prompt="prompt",
            )

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("ollama pull llama3.2", context.exception.detail)

    async def test_generate_text_returns_content_on_success(self) -> None:
        request = httpx.Request("POST", "http://ollama:11434/api/generate")
        response = httpx.Response(
            200,
            request=request,
            json={"response": "hello world"},
        )

        async def fake_post(*_args, **_kwargs):
            return response

        self.client._client.post = fake_post  # type: ignore[method-assign]

        content = await self.client.generate_text(
            system_prompt="system",
            user_prompt="prompt",
        )

        self.assertEqual(content, "hello world")


if __name__ == "__main__":
    unittest.main()