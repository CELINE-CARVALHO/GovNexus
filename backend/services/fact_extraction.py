
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.database.models.source_fact import (
    SourceFact,
    SourceSnapshot,
)
from backend.database.models.verification import FactDuplicateCandidate, ReviewTask


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_FACT_TYPES = {
    "service_information",
    "application_process",
    "eligibility",
    "required_document",
    "fee",
    "deadline",
    "contact_information",
    "location",
    "technical_information",
    "other",
}

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
        "fee",
        re.compile(
            r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "deadline",
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


class ExtractedFactPayload(BaseModel):
    source_snapshot_id: str
    fact_key: str = Field(min_length=8, max_length=200)
    fact_type: str = Field(min_length=2, max_length=60)
    value: dict = Field(default_factory=dict)
    language: str = Field(default="en", min_length=2, max_length=10)
    evidence_locator: dict = Field(default_factory=dict)
    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    extraction_status: str = Field(default="pending_review")

    @field_validator("fact_type")
    @classmethod
    def validate_fact_type(cls, value: str) -> str:
        fact_type = value.strip().lower()
        if fact_type not in ALLOWED_FACT_TYPES:
            raise ValueError(
                "Unsupported fact type. "
                f"Allowed values: {sorted(ALLOWED_FACT_TYPES)}"
            )
        return fact_type

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError("Fact value must be a dictionary.")
        if not value.get("text") or not str(value["text"]).strip():
            raise ValueError("Fact text is required.")
        return value

    @field_validator("evidence_locator")
    @classmethod
    def validate_evidence_locator(cls, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError("Evidence locator must be a dictionary.")
        if not value.get("quoted_text"):
            raise ValueError("Evidence excerpt is required.")
        return value


def normalize_fact_text(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.strip().lower())


def build_fact_key(fact_type: str, sentence: str) -> str:
    normalized = normalize_fact_text(sentence)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"{fact_type}:{digest}"


def find_existing_fact(db: Session, fact_key: str) -> SourceFact | None:
    return db.query(SourceFact).filter(SourceFact.fact_key == fact_key).first()


def validate_extracted_fact(fact_data: dict, source_text: str) -> dict:
    if not source_text or not source_text.strip():
        raise ValueError("Source content is empty, so no fact can be validated.")

    payload = ExtractedFactPayload.model_validate(fact_data)
    quoted = str(payload.evidence_locator.get("quoted_text", "")).strip()
    if quoted not in source_text:
        raise ValueError("Evidence excerpt is missing from the source snapshot text.")

    normalized_text = normalize_fact_text(str(payload.value.get("text", "")))
    if len(normalized_text) < 8:
        raise ValueError("Fact text is incomplete or truncated.")
    if normalized_text in {"", "null", "none"}:
        raise ValueError("Fact text is not usable.")

    return payload.model_dump()


def identify_duplicate_reason(left: str, right: str) -> tuple[str, float] | None:
    left_text = normalize_fact_text(left)
    right_text = normalize_fact_text(right)

    if left_text == right_text:
        return ("exact_duplicate", 1.0)

    similarity = SequenceMatcher(None, left_text, right_text).ratio()
    if similarity >= 0.96:
        return ("near_duplicate", similarity)
    if similarity >= 0.88:
        return ("repeated_across_snapshots", similarity)
    return None


def create_duplicate_suggestion(
    db: Session,
    source_fact: SourceFact,
    duplicate_fact: SourceFact,
    reason: str,
    similarity: float,
) -> None:
    existing = (
        db.query(FactDuplicateCandidate)
        .filter(
            FactDuplicateCandidate.source_fact_id == source_fact.id,
            FactDuplicateCandidate.duplicate_fact_id == duplicate_fact.id,
            FactDuplicateCandidate.reason == reason,
        )
        .first()
    )
    if existing:
        return

    db.add(
        FactDuplicateCandidate(
            source_fact_id=source_fact.id,
            duplicate_fact_id=duplicate_fact.id,
            similarity_score=round(similarity, 4),
            reason=reason,
            review_status="pending",
        )
    )


def detect_duplicate_candidates(db: Session, fact: SourceFact) -> list[str]:
    reasons: list[str] = []
    if not fact.value_data or not fact.value_data.get("text"):
        return reasons

    candidates = (
        db.query(SourceFact)
        .filter(SourceFact.id != fact.id, SourceFact.fact_type == fact.fact_type)
        .all()
    )

    for candidate in candidates:
        if not candidate.value_data or not candidate.value_data.get("text"):
            continue
        duplicate = identify_duplicate_reason(
            str(fact.value_data["text"]),
            str(candidate.value_data["text"]),
        )
        if not duplicate:
            continue
        reason, similarity = duplicate
        create_duplicate_suggestion(db, fact, candidate, reason, similarity)
        reasons.append(reason)

    return reasons


def resolve_snapshot_text_path(storage_uri: str) -> Path:
    relative_path = Path(storage_uri)

    if relative_path.is_absolute():
        raise ValueError("Absolute snapshot paths are not allowed.")

    candidate = (PROJECT_ROOT / relative_path).resolve()
    snapshot_root = (PROJECT_ROOT / "data" / "source_snapshots").resolve()

    if not candidate.is_relative_to(snapshot_root):
        raise ValueError("Snapshot path is outside the snapshot directory.")

    if candidate.suffix.lower() not in {".html", ".pdf"}:
        raise ValueError("Expected an HTML or PDF snapshot storage URI.")

    text_path = candidate.with_suffix(".txt")
    if not text_path.exists():
        raise FileNotFoundError(f"Extracted text file not found: {text_path}")

    return text_path


def split_into_sentences(text: str) -> list[tuple[str, int, int]]:
    results = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
        sentence = re.sub(r"\s+", " ", match.group(0)).strip()
        if len(sentence) < 35 or len(sentence) > 1200:
            continue
        results.append((sentence, match.start(), match.end()))
    return results


def classify_sentence(sentence: str) -> str | None:
    for pattern in EXCLUDED_PATTERNS:
        if pattern.search(sentence):
            return None

    for fact_type, pattern in FACT_PATTERNS:
        if pattern.search(sentence):
            return fact_type

    return None


def _build_extraction_candidate(
    source_text: str,
    fact_type: str,
    start: int,
    end: int,
) -> dict[str, Any] | None:
    """Build a fact candidate while preserving its exact source span."""
    raw_text = source_text[start:end]
    quoted_text = raw_text.strip()
    if not quoted_text:
        return None

    leading = len(raw_text) - len(raw_text.lstrip())
    trailing = len(raw_text.rstrip())
    character_start = start + leading
    character_end = start + trailing
    quoted_text = source_text[character_start:character_end]
    fact_text = re.sub(r"\s+", " ", quoted_text).strip()

    if len(fact_text) < 35:
        return None

    return {
        "fact_type": fact_type,
        "fact_text": fact_text,
        "character_start": character_start,
        "character_end": character_end,
        "quoted_text": quoted_text,
    }


def _non_empty_lines(source_text: str) -> list[tuple[int, int, str]]:
    """Return non-empty lines with offsets into the extracted snapshot text."""
    lines: list[tuple[int, int, str]] = []
    for match in re.finditer(r".*(?:\n|$)", source_text):
        raw_line = match.group(0)
        if not raw_line:
            continue
        line = raw_line[:-1] if raw_line.endswith("\n") else raw_line
        stripped = line.strip()
        if not stripped:
            continue
        line_start = match.start() + len(line) - len(line.lstrip())
        line_end = match.start() + len(line.rstrip())
        lines.append((line_start, line_end, stripped))
    return lines


def _uidai_structured_candidates(source_text: str) -> list[dict[str, Any]]:
    """Extract only explicit UIDAI field, age, and process blocks.

    These rules require a heading or a distinctive process boundary plus
    supporting content. They intentionally do not infer fees, deadlines,
    appointments, eligibility, or document lists.
    """
    lines = _non_empty_lines(source_text)
    candidates: list[dict[str, Any]] = []

    def add_block(fact_type: str, first: int, last: int) -> None:
        if first < 0 or last < first or last >= len(lines):
            return
        candidate = _build_extraction_candidate(
            source_text,
            fact_type,
            lines[first][0],
            lines[last][1],
        )
        if candidate:
            candidates.append(candidate)

    def first_line(predicate, start: int = 0) -> int | None:
        for index in range(start, len(lines)):
            if predicate(lines[index][2]):
                return index
        return None

    # A heading is accepted only when followed by its field list.
    for heading, fact_type in (
        ("demographic information", "service_information"),
        ("biometric information", "service_information"),
    ):
        heading_index = first_line(
            lambda value, heading=heading: value.lower() == heading
        )
        if heading_index is None or heading_index + 1 >= len(lines):
            continue
        next_index = heading_index + 1
        if lines[next_index][2].lower() in {
            "demographic information",
            "biometric information",
        }:
            continue
        add_block("service_information", heading_index, next_index)

    # Capture each explicit age boundary together with its supporting rule.
    age_pattern = re.compile(
        r"^age\s*(?:<\s*5|between\s+5\s+and\s+15|>\s*15)\s+years\b",
        re.IGNORECASE,
    )
    age_indexes = [
        index
        for index, (_, _, value) in enumerate(lines)
        if age_pattern.search(value)
    ]
    age_stop_pattern = re.compile(
        r"^(?:events like accidents|as the aadhaar authentication|"
        r"uidai may verify|aadhaar details that can be updated)",
        re.IGNORECASE,
    )
    for position, age_index in enumerate(age_indexes):
        next_age = (
            age_indexes[position + 1]
            if position + 1 < len(age_indexes)
            else len(lines)
        )
        end_index = next_age - 1
        for index in range(age_index + 1, next_age):
            if age_stop_pattern.search(lines[index][2]):
                end_index = index - 1
                break
        add_block("eligibility", age_index, end_index)

    biometric_event_index = first_line(
        lambda value: value.lower().startswith(
            "events like accidents or diseases"
        )
    )
    details_heading_index = first_line(
        lambda value: value.lower().startswith(
            "aadhaar details that can be updated"
        ),
        (biometric_event_index + 1) if biometric_event_index is not None else 0,
    )
    if biometric_event_index is not None and details_heading_index is not None:
        add_block(
            "service_information",
            biometric_event_index,
            details_heading_index - 1,
        )

    registered_index = first_line(
        lambda value: value.lower() == "registered mobile number"
    )
    if registered_index is not None:
        end_index = first_line(
            lambda value: value.lower().startswith("enabling aadhaar"),
            registered_index + 1,
        )
        if end_index is None:
            end_index = registered_index + 1
        add_block("application_process", registered_index + 1, end_index - 1)

    online_index = first_line(
        lambda value: value.lower() == "1. via online"
    )
    centre_index = first_line(
        lambda value: value.lower() == "by visiting aadhaar enrolment centre"
    )
    if online_index is not None and centre_index is not None and online_index < centre_index:
        add_block("application_process", online_index, centre_index - 1)

        online_start = lines[online_index][0]
        centre_start = lines[centre_index][0]
        supporting_match = re.search(
            r"to complete the update process.*?quality and processing team\.",
            source_text[online_start:centre_start],
            re.IGNORECASE | re.DOTALL,
        )
        if supporting_match:
            support_start = online_start + supporting_match.start()
            support_end = online_start + supporting_match.end()
            candidate = _build_extraction_candidate(
                source_text,
                "required_document",
                support_start,
                support_end,
            )
            if candidate:
                candidates.append(candidate)

        assisted_updates_index = first_line(
            lambda value: value.lower().startswith(
                "a. update client standard"
            ),
            centre_index + 1,
        )
        centre_end = (
            assisted_updates_index - 1
            if assisted_updates_index is not None
            else centre_index
        )
        add_block("application_process", centre_index, centre_end)

    return candidates


def extract_fact_candidates(source_text: str) -> list[dict[str, Any]]:
    """Return sentence and explicitly structured fact candidates.

    Existing sentence rules run first for compatibility. Structured rules are
    additive and are deduplicated by the existing fact-key algorithm.
    """
    candidates: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for sentence, start, end in split_into_sentences(source_text):
        fact_type = classify_sentence(sentence)
        if fact_type is None:
            continue
        candidate = _build_extraction_candidate(
            source_text,
            fact_type,
            start,
            end,
        )
        if candidate is None:
            continue
        fact_key = build_fact_key(fact_type, candidate["fact_text"])
        if fact_key in seen_keys:
            continue
        seen_keys.add(fact_key)
        candidates.append(candidate)

    for candidate in _uidai_structured_candidates(source_text):
        fact_key = build_fact_key(
            candidate["fact_type"],
            candidate["fact_text"],
        )
        if fact_key in seen_keys:
            continue
        seen_keys.add(fact_key)
        candidates.append(candidate)

    return candidates


def extract_snapshot_facts(db: Session, snapshot: SourceSnapshot) -> dict[str, Any]:
    source = snapshot.source
    if (
        source is None
        or not source.is_active
        or source.authority_status not in {"official", "authoritative", "verified"}
    ):
        return {
            "snapshot_id": str(snapshot.id),
            "status": "skipped",
            "reason": "Source is inactive or its authority has not been approved.",
            "created": 0,
            "existing": 0,
        }
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

    text_path = resolve_snapshot_text_path(snapshot.storage_uri)
    source_text = text_path.read_text(encoding="utf-8", errors="replace")

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

    for candidate in extract_fact_candidates(source_text):
        fact_type = candidate["fact_type"]
        fact_text = candidate["fact_text"]
        fact_key = build_fact_key(fact_type, fact_text)
        duplicate = find_existing_fact(db, fact_key)
        if duplicate:
            existing += 1
            continue

        fact_data = {
            "source_snapshot_id": str(snapshot.id),
            "fact_key": fact_key,
            "fact_type": fact_type,
            "value": {
                "text": fact_text,
                "language": "en",
                "review_required": True,
            },
            "language": "en",
            "evidence_locator": {
                "source_url": snapshot.source.url,
                "snapshot_id": str(snapshot.id),
                "file": str(text_path.relative_to(PROJECT_ROOT)),
                "character_start": candidate["character_start"],
                "character_end": candidate["character_end"],
                "quoted_text": candidate["quoted_text"],
            },
            "extraction_confidence": 0.5,
            "extraction_status": "pending_review",
        }

        try:
            validated = validate_extracted_fact(fact_data, source_text)
        except ValueError:
            continue

        fact = SourceFact(
            source_snapshot_id=snapshot.id,
            fact_key=validated["fact_key"],
            fact_type=validated["fact_type"],
            value_data=validated["value"],
            evidence_locator=validated["evidence_locator"],
            extraction_confidence=validated["extraction_confidence"],
            extraction_status=validated["extraction_status"],
        )

        db.add(fact)
        db.flush()

        detect_duplicate_candidates(db, fact)
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


def extract_selected_snapshot_facts(
    db: Session,
    *,
    snapshot_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    all_snapshots: bool = False,
) -> list[dict[str, Any]]:
    """Extract only explicitly selected snapshots unless --all is requested."""
    from sqlalchemy import false

    if all_snapshots and (snapshot_ids or source_ids):
        raise ValueError("Use --all or explicit IDs, not both.")
    if snapshot_ids and source_ids:
        raise ValueError("Select by snapshot IDs or source IDs, not both.")
    if not all_snapshots and not snapshot_ids and not source_ids:
        raise ValueError(
            "Select snapshots with snapshot_ids/source_ids or explicitly set all_snapshots=True."
        )

    try:
        parsed_snapshot_ids = [UUID(value) for value in (snapshot_ids or [])]
        parsed_source_ids = [UUID(value) for value in (source_ids or [])]
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("Snapshot and source IDs must be valid UUIDs.") from exc

    query = db.query(SourceSnapshot).filter(
        SourceSnapshot.http_status == 200,
        SourceSnapshot.extraction_status == "completed",
    )
    if parsed_snapshot_ids:
        query = query.filter(SourceSnapshot.id.in_(parsed_snapshot_ids))
    elif parsed_source_ids:
        query = query.filter(SourceSnapshot.source_id.in_(parsed_source_ids))
    elif not all_snapshots:
        query = query.filter(false())

    snapshots = query.order_by(SourceSnapshot.fetched_at.asc()).all()
    results = []
    for snapshot in snapshots:
        try:
            results.append(extract_snapshot_facts(db, snapshot))
        except Exception as exc:  # pragma: no cover - defensive path
            db.rollback()
            results.append({
                "snapshot_id": str(snapshot.id),
                "status": "failed",
                "error": str(exc),
                "created": 0,
                "existing": 0,
            })
    return results


def extract_all_snapshot_facts(db: Session) -> list[dict[str, Any]]:
    """Backward-compatible explicit all-snapshot API; CLI requires --all."""
    return extract_selected_snapshot_facts(db, all_snapshots=True)
