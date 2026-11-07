import asyncio

import httpx

from backend.api.v1 import chat
from backend.modules.ai.llm.gemini_client import GeminiProviderError
from backend.modules.ai.llm.groq_client import GroqClient, GroqProviderError


def _transport(handler):
    return httpx.MockTransport(handler)


def test_groq_rejects_a_model_that_is_not_listed():
    def handler(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "openai/gpt-oss-20b"}]})
        raise AssertionError("Chat must not be called for an unlisted model.")

    client = GroqClient(
        api_key="test-key",
        model="not-a-real-model",
        base_url="https://api.groq.com/openai/v1",
        transport=_transport(handler),
    )
    try:
        asyncio.run(client.generate("rules", "question"))
    except GroqProviderError as exc:
        assert "not in the provider model list" in str(exc)
    else:
        raise AssertionError("Unlisted model should fail before completion.")


def test_groq_is_used_before_gemini(monkeypatch):
    calls = []

    class GroqOk:
        configured = True
        provider_name = "groq"

        async def generate(self, system_instruction, user_prompt):
            calls.append("groq")
            return "The fee is listed. [S1]"

    class GeminiShouldNotRun:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            calls.append("gemini")
            raise AssertionError("Gemini must not run when Groq succeeds.")

    monkeypatch.setattr(chat, "GroqClient", lambda: GroqOk())
    monkeypatch.setattr(chat, "GeminiClient", lambda: GeminiShouldNotRun())
    evidence = [{
        "text": "The fee is listed.",
        "fact_type": "fee",
        "sources": [{
            "citation_marker": "[S1]",
            "publisher": "Gov",
            "url": "https://example.gov.in",
            "fact_id": "fact-a",
        }],
    }]
    answer = asyncio.run(chat.generate_grounded_answer("What is the fee?", "en", evidence))
    assert calls == ["groq"]
    assert "[S1]" in answer
    assert chat.last_generation_provider == "groq"


def test_gemini_runs_only_after_groq_fails(monkeypatch):
    calls = []

    class GroqDown:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            calls.append(("groq", user_prompt))
            raise GroqProviderError("down", retryable=True)

    class GeminiOk:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            calls.append(("gemini", user_prompt))
            return "The fee is listed. [S1]"

    monkeypatch.setattr(chat, "GroqClient", lambda: GroqDown())
    monkeypatch.setattr(chat, "GeminiClient", lambda: GeminiOk())
    evidence = [{
        "text": "The fee is listed.",
        "fact_type": "fee",
        "sources": [{
            "citation_marker": "[S1]",
            "publisher": "Gov",
            "url": "https://example.gov.in",
            "fact_id": "fact-a",
        }],
    }]
    answer = asyncio.run(chat.generate_grounded_answer("What is the fee?", "en", evidence))
    assert [name for name, _prompt in calls] == ["groq", "gemini"]
    assert calls[0][1] == calls[1][1]
    assert "evidence_untrusted_data" in calls[1][1]
    assert "[S1]" in answer
    assert chat.last_generation_provider == "gemini"


def test_both_providers_failing_raises_instead_of_inventing_an_answer(monkeypatch):
    class GroqDown:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            raise GroqProviderError("down", retryable=True)

    class GeminiDown:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            raise GeminiProviderError("down", retryable=True)

    monkeypatch.setattr(chat, "GroqClient", lambda: GroqDown())
    monkeypatch.setattr(chat, "GeminiClient", lambda: GeminiDown())
    evidence = [{
        "text": "The fee is listed.",
        "fact_type": "fee",
        "sources": [{
            "citation_marker": "[S1]",
            "publisher": "Gov",
            "url": "https://example.gov.in",
            "fact_id": "fact-a",
        }],
    }]
    try:
        asyncio.run(chat.generate_grounded_answer("What is the fee?", "en", evidence))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 503
    else:
        raise AssertionError("Both providers failing must not invent an answer.")
