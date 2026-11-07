from __future__ import annotations

import asyncio
from io import BytesIO
import wave

import httpx
import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile

from backend.api.v1 import voice


def wav_bytes(seconds: float = 0.2) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000)
        file.writeframes(b"\0\0" * int(16000 * seconds))
    return output.getvalue()


def upload_audio(
    content: bytes | None = None,
    *,
    filename: str = "speech.wav",
    content_type: str = "audio/wav",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(wav_bytes() if content is None else content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class MockAsyncClient:
    response: httpx.Response | None = None
    error: Exception | None = None
    requests: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.requests.append({"url": url, **kwargs})
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch):
    MockAsyncClient.response = None
    MockAsyncClient.error = None
    MockAsyncClient.requests = []
    monkeypatch.setattr(voice.httpx, "AsyncClient", MockAsyncClient)
    monkeypatch.setattr(voice.settings, "GNANI_API_KEY_ID", "test-key-id")


def provider_response(status: int = 200, json: dict | None = None, content=b"", headers=None):
    return httpx.Response(
        status,
        json=json,
        content=content if json is None else None,
        headers=headers,
        request=httpx.Request("POST", "https://provider.test"),
    )


def test_stt_sends_documented_multipart_fields_and_returns_detected_language():
    MockAsyncClient.response = provider_response(
        json={
            "success": True,
            "transcript": "नमस्ते",
            "detected_language_code": "hi-IN",
            "request_id": "request-123",
        }
    )

    result = asyncio.run(
        voice.transcribe_audio(
            upload_audio(),
            language_code="hi-IN",
            format="transcribe",
        )
    )

    request = MockAsyncClient.requests[0]
    assert request["url"] == "https://api.vachana.ai/stt/v3"
    assert request["headers"]["X-API-Key-ID"] == "test-key-id"
    assert request["data"] == {
        "model": "prisma-v3.0",
        "language_code": "hi-IN",
        "format": "transcribe",
        "itn_native_numerals": "false",
    }
    assert request["files"]["audio_file"][0] == "speech.wav"
    assert result["transcript"] == "नमस्ते"
    assert result["detected_language_code"] == "hi-IN"


def test_stt_rejects_unsupported_audio_format():
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(filename="clip.webm", content_type="audio/webm"),
                language_code="en-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 415


def test_stt_rejects_audio_larger_than_limit():
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(
                    b"x" * (voice.MAX_AUDIO_BYTES + 1),
                    filename="speech.wav",
                ),
                language_code="en-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 413


def test_stt_rejects_wav_longer_than_provider_duration_limit():
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(wav_bytes(31)),
                language_code="en-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 413


def test_stt_auto_detects_language_and_keeps_the_detected_code():
    MockAsyncClient.response = provider_response(
        json={"success": True, "transcript": "ನಮಸ್ಕಾರ", "request_id": "request-kn"}
    )
    result = asyncio.run(
        voice.transcribe_audio(
            upload_audio(),
            language_code="indic-auto",
            format="transcribe",
        )
    )
    assert MockAsyncClient.requests[0]["data"]["language_code"] == "indic-auto"
    assert result["detected_language_code"] == "kn-IN"
    assert result["transcript"] == "ನಮಸ್ಕಾರ"


def test_stt_rejects_unsupported_language():
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(),
                language_code="as-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 422


def test_stt_timeout_is_reported_without_provider_details():
    MockAsyncClient.error = httpx.TimeoutException("provider details")
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(),
                language_code="en-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 504
    assert "provider details" not in error.value.detail


def test_stt_provider_error_is_handled():
    MockAsyncClient.response = provider_response(
        status=400,
        json={
            "success": False,
            "error": {"type": "INVALID_FORMAT", "message": "Unsupported format."},
        },
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.transcribe_audio(
                upload_audio(),
                language_code="en-IN",
                format="transcribe",
            )
        )
    assert error.value.status_code == 502
    assert error.value.detail == "Unsupported format."


@pytest.mark.parametrize(
    ("language", "expected_voice"),
    [
        ("bn-IN", "Kirra"),
        ("en-IN", "Kaveri"),
        ("gu-IN", "Falak"),
        ("hi-IN", "Nalini"),
        ("kn-IN", "Saanvi"),
        ("ml-IN", "Reshma"),
        ("mr-IN", "Zahira"),
        ("pa-IN", "Mehuli"),
        ("ta-IN", "Asmita"),
        ("te-IN", "Suhana"),
    ],
)
def test_tts_uses_documented_voice_and_returns_wav(language, expected_voice):
    audio = b"RIFF\x00\x00\x00\x00WAVE"
    MockAsyncClient.response = provider_response(
        content=audio,
        headers={"content-type": "audio/wav"},
    )
    payload = voice.SynthesizeRequest(
        text="  Verified response.  ",
        language_code=language,
    )

    response = asyncio.run(voice.synthesize_speech(payload))

    request = MockAsyncClient.requests[0]
    assert request["url"] == "https://api.vachana.ai/api/v1/tts/inference"
    assert request["headers"]["X-API-Key-ID"] == "test-key-id"
    assert request["json"]["text"] == "Verified response."
    assert request["json"]["voice"] == expected_voice
    assert request["json"]["language"] == language
    assert request["json"]["model"] == "timbre-v2.5"
    assert response.body == audio
    assert response.media_type == "audio/wav"
    assert response.headers["cache-control"] == "no-store"


def test_tts_rejects_unsupported_language():
    with pytest.raises(ValueError):
        voice.SynthesizeRequest(text="Hello", language_code="as-IN")


def test_tts_rejects_blank_or_oversized_text():
    with pytest.raises(ValueError):
        voice.SynthesizeRequest(text="   ", language_code="en-IN")
    with pytest.raises(ValueError):
        voice.SynthesizeRequest(text="x" * (voice.MAX_TTS_TEXT_LENGTH + 1))


def test_tts_provider_failure_is_reported():
    MockAsyncClient.error = httpx.RequestError("provider details")
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.synthesize_speech(
                voice.SynthesizeRequest(text="Verified response.")
            )
        )
    assert error.value.status_code == 502
    assert "provider details" not in error.value.detail


def test_tts_rejects_non_audio_provider_response():
    MockAsyncClient.response = provider_response(
        content=b'{"detail":"not audio"}',
        headers={"content-type": "application/json"},
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            voice.synthesize_speech(
                voice.SynthesizeRequest(text="Verified response.")
            )
        )
    assert error.value.status_code == 502
