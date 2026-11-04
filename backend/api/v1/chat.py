
from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.database.models.source import Source
from backend.database.models.source_fact import SourceFact, SourceSnapshot
from backend.database.models.verification import FactVerification


router = APIRouter(prefix="/chat", tags=["SchemeSathi Assistant"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    language_code: str = Field(default="en-IN", max_length=10)


class Citation(BaseModel):
    publisher: str
    url: str
    fact_id: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    evidence_found: bool
    grounded: bool


INSUFFICIENT_EVIDENCE = (
    "I could not find sufficiently verified official information "
    "to answer this question yet. I don't want to give you incorrect "
    "government-service guidance. Please try again later or consult "
    "the relevant official government department."
)


def retrieve_verified_facts(
    db: Session,
    question: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    # Select the latest verification timestamp for each fact.
    latest_verification = (
        db.query(
            FactVerification.source_fact_id.label("fact_id"),
            func.max(FactVerification.verified_at).label("latest_at"),
        )
        .group_by(FactVerification.source_fact_id)
        .subquery()
    )

    query = (
        db.query(SourceFact, SourceSnapshot, Source, FactVerification)
        .join(
            SourceSnapshot,
            SourceSnapshot.id == SourceFact.source_snapshot_id,
        )
        .join(Source, Source.id == SourceSnapshot.source_id)
        .join(
            latest_verification,
            latest_verification.c.fact_id == SourceFact.id,
        )
        .join(
            FactVerification,
            and_(
                FactVerification.source_fact_id == SourceFact.id,
                FactVerification.verified_at
                == latest_verification.c.latest_at,
            ),
        )
        .filter(
            FactVerification.verification_status == "verified",
            func.lower(FactVerification.decision).in_(
                ["approved", "approve", "accepted", "accept"]
            ),
            Source.is_active.is_(True),
        )
    )

    # Basic database-side relevance matching.
    terms = [
        term.lower()
        for term in question.split()
        if len(term) >= 3
    ][:8]

    if terms:
        relevance_conditions = []

        for term in terms:
            pattern = f"%{term}%"
            relevance_conditions.extend(
                [
                    SourceFact.fact_key.ilike(pattern),
                    SourceFact.fact_type.ilike(pattern),
                    func.cast(SourceFact.value_data, type_=__import__(
                        "sqlalchemy"
                    ).String).ilike(pattern),
                ]
            )

        query = query.filter(
            __import__("sqlalchemy").or_(*relevance_conditions)
        )

    rows = (
        query
        .order_by(FactVerification.verified_at.desc())
        .limit(limit)
        .all()
    )

    evidence = []

    for fact, snapshot, source, verification in rows:
        evidence.append(
            {
                "fact_id": str(fact.id),
                "fact_key": fact.fact_key,
                "fact_type": fact.fact_type,
                "value": fact.value_data,
                "evidence_locator": fact.evidence_locator,
                "publisher": source.publisher_name,
                "source_url": source.url,
                "source_type": source.source_type,
                "authority_status": source.authority_status,
                "snapshot_fetched_at": (
                    snapshot.fetched_at.isoformat()
                    if snapshot.fetched_at
                    else None
                ),
                "verified_at": (
                    verification.verified_at.isoformat()
                    if verification.verified_at
                    else None
                ),
            }
        )

    return evidence


async def generate_grounded_answer(
    question: str,
    language_code: str,
    evidence: list[dict[str, Any]],
) -> str:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured.",
        )

    if not settings.GEMINI_MODEL:
        raise HTTPException(
            status_code=503,
            detail="Gemini model is not configured.",
        )

    evidence_text = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    prompt = f"""
You are SchemeSathi, an assistant that guides people through
Indian government services.

STRICT RULES:
1. Answer using ONLY the supplied verified evidence.
2. Never invent eligibility rules, fees, deadlines, documents,
   office addresses, procedures, or application links.
3. If the evidence does not answer a part of the question,
   explicitly say that the information is not available.
4. Cite supporting evidence using [S1], [S2], etc.
5. Do not fabricate citations.
6. Distinguish confirmed facts from uncertainty.
7. Use clear, simple language suitable for ordinary citizens.
8. Reply in the language requested by the language code.
9. Do not claim that an application has been submitted or approved.

Requested language: {language_code}

Citizen's question:
{question}

Verified evidence:
{evidence_text}

Write a helpful answer with source markers.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{settings.GEMINI_MODEL}:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                url,
                params={"key": settings.GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1200,
                    },
                },
            )

        if response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily busy. Please retry later.",
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail="The AI service could not generate a response.",
            )

        data = response.json()

        answer = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="The AI service returned an empty response.",
            )

        return answer

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="The AI service took too long to respond.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to the AI service.",
        )


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    evidence = retrieve_verified_facts(
        db=db,
        question=payload.message,
    )

    # Do not call Gemini when there is no verified evidence.
    if not evidence:
        return ChatResponse(
            answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            evidence_found=False,
            grounded=False,
        )

    answer = await generate_grounded_answer(
        question=payload.message,
        language_code=payload.language_code,
        evidence=evidence,
    )

    citations = [
        Citation(
            publisher=item["publisher"],
            url=item["source_url"],
            fact_id=item["fact_id"],
        )
        for item in evidence
    ]

    return ChatResponse(
        answer=answer,
        citations=citations,
        evidence_found=True,
        grounded=True,
    )
