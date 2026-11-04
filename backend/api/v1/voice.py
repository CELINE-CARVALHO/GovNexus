from typing import Literal

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.config import settings


router = APIRouter(prefix="/voice", tags=["Gnani Voice"])

SUPPORTED_LANGUAGES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
    "ml-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN",
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

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "application/ogg",
    "audio/flac",
    "audio/aac",
    "audio/mp4",
    "audio/x-m4a",
}


def require_gnani_key() -> str:
    key = settings.GNANI_API_KEY_ID.strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Gnani API key is not configured on the server.",
        )
    return key


def raise_gnani_error(response: httpx.Response, service: str):
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message")
        if not message:
            message = payload.get("detail") or payload.get("message")
    except Exception:
        message = None

    if response.status_code == 401 or response.status_code == 403:
        detail = "Gnani authentication failed. Check the API key ID."
    elif response.status_code == 429:
        detail = f"Gnani {service} rate limit reached. Please try again shortly."
    elif response.status_code >= 500:
        detail = f"Gnani {service} is temporarily unavailable."
    else:
        detail = message or f"Gnani {service} rejected the request."

    raise HTTPException(status_code=502, detail=detail)


@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language_code: str = Form(...),
    audio_format: Literal["verbatim", "transcribe"] = Form("transcribe"),
):
    if language_code not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported language. Choose one of the ten Gnani Prisma languages.",
        )

    content_type = (audio_file.content_type or "").lower().split(";")[0]
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio format. Upload WAV, MP3, OGG, FLAC, AAC or M4A.",
        )

    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The uploaded audio is empty.")

    if len(audio_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio upload exceeds 15 MB.")

    api_key = require_gnani_key()

    files = {
        "audio_file": (
            audio_file.filename or "recording.wav",
            audio_bytes,
            content_type,
        )
    }
    data = {
        "language_code": language_code,
        "format": audio_format,
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
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gnani transcription timed out.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach Gnani Prisma.")

    if response.status_code != 200:
        raise_gnani_error(response, "Prisma transcription")

    try:
        result = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Gnani returned an invalid response.")

    transcript = (result.get("transcript") or "").strip()
    if not result.get("success") or not transcript:
        raise HTTPException(
            status_code=422,
            detail="No speech could be transcribed. Please try recording again.",
        )

    return {
        "success": True,
        "provider": "Gnani Prisma",
        "request_id": result.get("request_id"),
        "language_code": language_code,
        "transcript": transcript,
    }


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language_code: str = "en-IN"
    speed: float = Field(default=1.0, ge=0.85, le=1.15)


@router.post("/synthesize")
async def synthesize_speech(payload: SynthesizeRequest):
    if payload.language_code not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported language. Choose one of the ten Gnani Timbre languages.",
        )

    api_key = require_gnani_key()
    voice = VOICE_BY_LANGUAGE[payload.language_code]

    request_body = {
        "text": payload.text.strip(),
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

    headers = {
        "X-API-Key-ID": api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.GNANI_REQUEST_TIMEOUT
        ) as client:
            response = await client.post(
                settings.GNANI_TTS_URL,
                headers=headers,
                json=request_body,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gnani speech generation timed out.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach Gnani Timbre.")

    if response.status_code != 200:
        raise_gnani_error(response, "Timbre speech generation")

    if not response.content:
        raise HTTPException(status_code=502, detail="Gnani returned empty audio.")

    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "audio/wav"),
        headers={"Cache-Control": "no-store"},
    )
