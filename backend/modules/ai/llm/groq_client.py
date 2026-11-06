"""Groq chat client. OpenAI-compatible endpoint documented at
https://console.groq.com/docs/api-reference.
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import settings


class GroqProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class GroqClient:
    provider_name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = settings.GROQ_API_KEY if api_key is None else api_key
        self.model = settings.GROQ_MODEL if model is None else model
        self.base_url = (
            settings.GROQ_BASE_URL if base_url is None else base_url
        ).rstrip("/")
        self.timeout = settings.GROQ_TIMEOUT_SECONDS if timeout is None else timeout
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.model.strip() and self.base_url)

    def _headers(self) -> dict[str, str]:
        if not self.api_key.strip():
            raise GroqProviderError("Groq is not configured.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_model_ids(self) -> set[str]:
        if not self.configured:
            raise GroqProviderError("Groq is not configured.")
        payload = await self._request("GET", f"{self.base_url}/models")
        data = payload.get("data")
        if not isinstance(data, list):
            raise GroqProviderError("Groq returned an invalid model list.")
        return {
            item["id"]
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    async def generate(self, system_instruction: str, user_prompt: str) -> str:
        if not self.configured:
            raise GroqProviderError("Groq generation is not configured.")
        try:
            available = await self.list_model_ids()
        except GroqProviderError:
            raise
        if self.model not in available:
            raise GroqProviderError(
                "Configured Groq model is not in the provider model list."
            )
        payload = await self._request(
            "POST",
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "temperature": 0.1,
                "max_tokens": 1200,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        try:
            text = payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise GroqProviderError("Groq returned a malformed response.") from exc
        if not text:
            raise GroqProviderError("Groq returned an empty response.")
        return text

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=json,
                )
        except httpx.TimeoutException as exc:
            raise GroqProviderError("Groq request timed out.", retryable=True) from exc
        except httpx.RequestError as exc:
            raise GroqProviderError("Groq request failed.", retryable=True) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise GroqProviderError("Groq is temporarily unavailable.", retryable=True)
        if response.status_code >= 400:
            raise GroqProviderError("Groq rejected the request.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GroqProviderError("Groq returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise GroqProviderError("Groq returned an invalid response.")
        return payload
