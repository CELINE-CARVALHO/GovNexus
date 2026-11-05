from __future__ import annotations

from typing import Any

import httpx

from backend.config import settings


class GeminiProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class GeminiClient:
    API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        timeout: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.model = settings.GEMINI_MODEL if model is None else model
        self.embedding_model = (
            settings.GEMINI_EMBEDDING_MODEL
            if embedding_model is None
            else embedding_model
        )
        self.timeout = (
            settings.GEMINI_TIMEOUT_SECONDS if timeout is None else timeout
        )
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise GeminiProviderError("Gemini is not configured.")
        return {"x-goog-api-key": self.api_key}

    async def generate(self, system_instruction: str, user_prompt: str) -> str:
        if not self.configured:
            raise GeminiProviderError("Gemini generation is not configured.")

        model = self.model.removeprefix("models/")
        url = f"{self.API_ROOT}/models/{model}:generateContent"
        request_body = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1200,
            },
        }

        data = await self._request("POST", url, json=request_body)
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise GeminiProviderError(
                "Gemini returned a malformed response."
            ) from exc
        if not text:
            raise GeminiProviderError("Gemini returned an empty response.")
        return text

    async def embed(self, text: str, *, task_type: str) -> list[float]:
        vectors = await self.embed_many([text], task_type=task_type)
        return vectors[0]

    async def embed_many(
        self,
        texts: list[str],
        *,
        task_type: str,
    ) -> list[list[float]]:
        if not self.api_key or not self.embedding_model:
            raise GeminiProviderError("Gemini embeddings are not configured.")
        if not texts:
            return []

        model = self.embedding_model.removeprefix("models/")
        requests = [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
            }
            for text in texts
        ]
        url = f"{self.API_ROOT}/models/{model}:batchEmbedContents"
        data = await self._request(
            "POST",
            url,
            json={"requests": requests},
        )
        try:
            embeddings = [
                [float(value) for value in item["values"]]
                for item in data["embeddings"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise GeminiProviderError(
                "Gemini returned malformed embeddings."
            ) from exc
        if len(embeddings) != len(texts) or any(not vector for vector in embeddings):
            raise GeminiProviderError(
                "Gemini returned an incomplete embedding batch."
            )
        return embeddings

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any],
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
            raise GeminiProviderError(
                "Gemini request timed out.",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise GeminiProviderError(
                "Gemini request failed.",
                retryable=True,
            ) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise GeminiProviderError(
                "Gemini is temporarily unavailable.",
                retryable=True,
            )
        if response.status_code >= 400:
            raise GeminiProviderError("Gemini rejected the request.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GeminiProviderError(
                "Gemini returned invalid JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise GeminiProviderError("Gemini returned an invalid response.")
        return payload