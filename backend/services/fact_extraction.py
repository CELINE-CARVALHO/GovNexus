
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.database.models.source_fact import (
    SourceFact,
    SourceSnapshot,
)
from backend.database.models.verification import ReviewTask


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Navigation, interface and generic website text is not useful
# evidence of a government service requirement.
EXCLUDED_PATTERNS = [
    re.compile(
        r"\b(know your|click here|learn more|read more|"
        r"javascript must be enabled|access this site|"
        r"nearest to your location|download the app|"
        r"play store|app store|customer login)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(how to|what details are required for onboarding)\s*$",
        re.IGNORECASE,
    ),
]

FACT_PATTERNS = [
    (
        "required_document",
        re.compile(
            r"\b(required documents?|documents required|"
            r"must submit|must upload|proof of identity|"
            r"proof of address|supporting documents?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "eligibility",
        re.compile(
            r"\b(eligible if|eligibility criteria|"
            r"minimum age|maximum age|must belong to|"
            r"only students who|applicants must|"
            r"annual family income|income limit)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "fee_or_amount",
        re.compile(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "deadline_or_date",
        re.compile(
            r"\b(last date to apply|application deadline|"
            r"applications close|valid until|valid till|"
            r"deadline for submission)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "contact_information",
        re.compile(
            r"\b(helpline number|toll.?free number|"
            r"official email address|grievance officer|"
            r"contact number)\b",
            re.IGNORECASE,
        ),
    ),
        (
            "application_process",
            re.compile(
                r"\b(mandatory to (apply|avail|access|receive)|"
                r"required to apply|must apply|"
                r"apply through|submit an application|"
                r"registration is mandatory|"
                r"register before applying|"
                r"login with .* to apply|"
                r"steps to apply)\b",
                re.IGNORECASE,
            ),
        ),
    (
        "service_information",
        re.compile(
            r"\b(is a unique|is used for|"
            r"is applicable for|allows users to|"
            r"provides the facility|"
            r"enables users to|issued by|"
            r"helps applicants|academic career)\b",
            re.IGNORECASE,
        ),
    ),
]


def resolve_snapshot_text_path(storage_uri: str) -> Path:
    relative_path = Path(storage_uri)

    if relative_path.is_absolute():
        raise ValueError("Absolute snapshot paths are not allowed.")

    candidate = (PROJECT_ROOT / relative_path).resolve()

    snapshot_root = (
        PROJECT_ROOT / "data" / "source_snapshots"
    ).resolve()

    if not candidate.is_relative_to(snapshot_root):
        raise ValueError(
            "Snapshot path is outside the snapshot directory."
        )

    if candidate.suffix.lower() != ".html":
        raise ValueError("Expected an HTML snapshot storage URI.")

    text_path = candidate.with_suffix(".txt")

    if not text_path.exists():
        raise FileNotFoundError(
            f"Extracted text file not found: {text_path}"
        )

    return text_path


def split_into_sentences(
    text: str,
) -> list[tuple[str, int, int]]:
    results = []

    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        sentence = re.sub(
            r"\s+",
            " ",
            match.group(0),
        ).strip()

        if len(sentence) < 35 or len(sentence) > 1200:
            continue

        results.append(
            (sentence, match.start(), match.end())
        )

    return results


def classify_sentence(sentence: str) -> str | None:
    for pattern in EXCLUDED_PATTERNS:
        if pattern.search(sentence):
            return None

    for fact_type, pattern in FACT_PATTERNS:
        if pattern.search(sentence):
            return fact_type

    return None


def normalize_fact_text(sentence: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        sentence.strip().lower(),
    )


def build_fact_key(
    fact_type: str,
    sentence: str,
) -> str:
    normalized = normalize_fact_text(sentence)

    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:32]

    return f"{fact_type}:{digest}"


def find_existing_fact(
    db: Session,
    fact_key: str,
) -> SourceFact | None:
    # Search across snapshots, not just the current snapshot.
    return (
        db.query(SourceFact)
        .filter(SourceFact.fact_key == fact_key)
        .first()
    )


def extract_snapshot_facts(
    db: Session,
    snapshot: SourceSnapshot,
) -> dict[str, Any]:

    if snapshot.http_status != 200:
        return {
            "snapshot_id": str(snapshot.id),
            "status": "skipped",
            "reason": "Snapshot was not fetched successfully.",
            "created": 0,
            "existing": 0,
        }

    if snapshot.extraction_status != "completed":
        return {
            "snapshot_id": str(snapshot.id),
            "status": "skipped",
            "reason": "Snapshot extraction is incomplete.",
            "created": 0,
            "existing": 0,
        }

    text_path = resolve_snapshot_text_path(
        snapshot.storage_uri
    )

    source_text = text_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if not source_text.strip():
        return {
            "snapshot_id": str(snapshot.id),
            "status": "skipped",
            "reason": "Snapshot text is empty.",
            "created": 0,
            "existing": 0,
        }

    created = 0
    existing = 0

    for sentence, start, end in split_into_sentences(source_text):

        fact_type = classify_sentence(sentence)

        if fact_type is None:
            continue

        fact_key = build_fact_key(
            fact_type,
            sentence,
        )

        duplicate = find_existing_fact(
            db,
            fact_key,
        )

        if duplicate:
            existing += 1
            continue

        fact = SourceFact(
            source_snapshot_id=snapshot.id,
            fact_key=fact_key,
            fact_type=fact_type,
            value_data={
                "text": sentence,
                "language": "en",
                "review_required": True,
            },
            evidence_locator={
                "file": str(
                    text_path.relative_to(PROJECT_ROOT)
                ),
                "character_start": start,
                "character_end": end,
                "quoted_text": sentence,
            },
            extraction_confidence=None,
            extraction_status="pending_review",
        )

        db.add(fact)
        db.flush()

        db.add(
            ReviewTask(
                source_fact_id=fact.id,
                task_type="fact_verification",
                status="open",
                priority="normal",
            )
        )

        created += 1

    db.commit()

    return {
        "snapshot_id": str(snapshot.id),
        "status": "completed",
        "created": created,
        "existing": existing,
    }


def extract_all_snapshot_facts(
    db: Session,
) -> list[dict[str, Any]]:

    snapshots = (
        db.query(SourceSnapshot)
        .filter(
            SourceSnapshot.http_status == 200,
            SourceSnapshot.extraction_status == "completed",
        )
        .order_by(SourceSnapshot.fetched_at.asc())
        .all()
    )

    results = []

    for snapshot in snapshots:
        try:
            result = extract_snapshot_facts(
                db,
                snapshot,
            )

            results.append(result)

        except Exception as exc:
            db.rollback()

            results.append({
                "snapshot_id": str(snapshot.id),
                "status": "failed",
                "error": str(exc),
                "created": 0,
                "existing": 0,
            })

    return results
