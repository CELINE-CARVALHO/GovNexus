from __future__ import annotations

from io import BytesIO
from typing import Literal
import wave

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from backend.config import settings


router = APIRouter(prefix="/voice", tags=["Prism Voice"])

SUPPORTED_LANGUAGES = {
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
}

VOICE_BY_LANGUAGE = {
    "bn-IN": "Kirra",
    "en-IN": "Kaveri",
    "gu-IN": "Falak",
    "hi-IN": "Nalini",
    "kn-IN": "Saanvi",
    "ml-IN": "Reshma",
    "mr-IN": "Zahira",
    "pa-IN": "Mehuli",
    "ta-IN": "Asmita",
    "te-IN": "Suhana",
}

AUDIO_TYPE_EXTENSIONS = {
    "audio/wav": {".wav"},
    "audio/x-wav": {".wav"},
    "audio/mpeg": {".mp3"},
    "audio/mp3": {".mp3"},
    "audio/ogg": {".ogg"},
    "application/ogg": {".ogg"},
    "audio/flac": {".flac"},
    "audio/x-flac": {".flac"},
    "audio/aac": {".aac"},
    "audio/mp4": {".m4a", ".mp4"},
    "audio/x-m4a": {".m4a"},
}
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_AUDIO_DURATION_SECONDS = 30
MAX_TTS_TEXT_LENGTH = 5000


def require_gnani_key() -> str:
    key = settings.GNANI_API_KEY_ID.strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Prism speech is not configured on the server.",
        )
    return key


def _validate_wav_duration(content: bytes) -> None:
    try:
        with wave.open(BytesIO(content), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
    except (wave.Error, EOFError, ZeroDivisionError) as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded WAV file is malformed.",
        ) from exc
    if duration > MAX_AUDIO_DURATION_SECONDS:
        raise HTTPException(
            status_code=413,
            detail="Audio must be no longer than 30 seconds.",
        )


def _provider_error_detail(response: httpx.Response, service: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(error, dict):
        error = {}
    message = error.get("message")
    if not isinstance(message, str) and isinstance(payload, dict):
        message = payload.get("detail") or payload.get("message")
    if isinstance(message, str):
        message = message.strip()

    if response.status_code in {401, 403}:
        return "Prism authentication failed. Check the server voice credential."
    if response.status_code == 429:
        return f"Prism {service} rate limit reached. Please try again shortly."
    if response.status_code >= 500:
        return f"Prism {service} is temporarily unavailable."
    if response.status_code in {413, 422}:
        return message or f"Prism {service} rejected the supplied media."
    return message or f"Prism {service} rejected the request."


def _raise_gnani_error(response: httpx.Response, service: str) -> None:
    raise HTTPException(
        status_code=502,
        detail=_provider_error_detail(response, service),
    )


@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language_code: str = Form(...),
    format: Literal["verbatim", "transcribe"] = Form("transcribe"),
):
    if language_code not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported language. Choose one of the ten Prism languages.",
        )

    content_type = (audio_file.content_type or "").lower().split(";")[0].strip()
    allowed_extensions = AUDIO_TYPE_EXTENSIONS.get(content_type)
    if not allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format. Upload WAV, MP3, OGG, FLAC, AAC or M4A.",
        )

    filename = (audio_file.filename or "").lower()
    extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail="Audio filename extension does not match its supported format.",
        )

    audio_bytes = await audio_file.read(MAX_AUDIO_BYTES + 1)
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The uploaded audio is empty.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio upload exceeds 10 MB.")
    if content_type in {"audio/wav", "audio/x-wav"}:
        _validate_wav_duration(audio_bytes)

    api_key = require_gnani_key()
    files = {
        "audio_file": (
            audio_file.filename or f"recording{extension}",
            audio_bytes,
            content_type,
        )
    }
    if settings.GNANI_STT_MODEL not in {"prisma-v2.5", "prisma-v3.0"}:
        raise HTTPException(
            status_code=503,
            detail="Prism speech model configuration is invalid.",
        )
    data = {
        "model": settings.GNANI_STT_MODEL,
        "language_code": language_code,
        "format": format,
        "itn_native_numerals": "false",
    }
    headers = {"X-API-Key-ID": api_key}

    try:
        async with httpx.AsyncClient(
            timeout=settings.GNANI_REQUEST_TIMEOUT
        ) as client:
            response = await client.post(
                settings.GNANI_STT_URL,
                headers=headers,
                data=data,
                files=files,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Prism transcription timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Prism speech recognition.",
        ) from exc

    if response.status_code != 200:
        _raise_gnani_error(response, "Prisma transcription")
    try:
        result = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Prism returned an invalid response.",
        ) from exc
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=502,
            detail="Prism returned an invalid response.",
        )
    if result.get("truncated"):
        raise HTTPException(
            status_code=422,
            detail="The transcription was truncated. Please record a shorter question.",
        )

    transcript = result.get("transcript")
    if not result.get("success") or not isinstance(transcript, str) or not transcript.strip():
        raise HTTPException(
            status_code=422,
            detail="No speech could be transcribed. Please try recording again.",
        )

    return {
        "success": True,
        "provider": "Prism",
        "request_id": result.get("request_id"),
        "language_code": language_code,
        "detected_language_code": result.get("detected_language_code"),
        "transcript": transcript.strip(),
    }


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    language_code: str = "en-IN"
    speed: float = Field(default=1.0, ge=0.85, le=1.15)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Text to synthesize cannot be blank.")
        return normalized

    @field_validator("language_code")
    @classmethod
    def validate_language_code(cls, value: str) -> str:
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(
                "Unsupported language. Choose one of the ten Prism languages."
            )
        return value


@router.post("/synthesize")
async def synthesize_speech(payload: SynthesizeRequest):
    api_key = require_gnani_key()
    voice = VOICE_BY_LANGUAGE[payload.language_code]
    request_body = {
        "text": payload.text,
        "model": settings.GNANI_TTS_MODEL,
        "voice": voice,
        "language": payload.language_code,
        "speed": payload.speed,
        "audio_config": {
            "encoding": "linear_pcm",
            "container": "wav",
            "num_channels": 1,
            "sample_rate": 48000,
            "sample_width": 2,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.GNANI_REQUEST_TIMEOUT
        ) as client:
            response = await client.post(
                settings.GNANI_TTS_URL,
                headers={"X-API-Key-ID": api_key},
                json=request_body,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Prism speech generation timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Prism speech synthesis.",
        ) from exc

    if response.status_code != 200:
        _raise_gnani_error(response, "speech generation")
    if not response.content:
        raise HTTPException(status_code=502, detail="Prism returned empty audio.")

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "audio/wav":
        raise HTTPException(
            status_code=502,
            detail="Prism returned an unsupported audio format.",
        )
    return Response(
        content=response.content,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="govnexus-response.wav"',
        },
    )
