from datetime import date
from types import SimpleNamespace

import pytest

from backend.api.v1.services import validate_service_version_for_publication
from backend.services.fact_extraction import identify_duplicate_reason, validate_extracted_fact


def test_validate_extracted_fact_accepts_with_matching_excerpt():
    source_text = (
        "Applicants must submit proof of identity and proof of address. "
        "The last date to apply is 31 July 2026."
    )
    fact_data = {
        "source_snapshot_id": "11111111-1111-4111-8111-111111111111",
        "fact_key": "required_document:deadbeef",
        "fact_type": "required_document",
        "value": {
            "text": "Applicants must submit proof of identity and proof of address.",
            "language": "en",
            "review_required": True,
        },
        "language": "en",
        "evidence_locator": {
            "source_url": "https://example.gov.in",
            "file": "data/source_snapshots/source/abc.txt",
            "quoted_text": "Applicants must submit proof of identity and proof of address.",
        },
        "extraction_confidence": 0.87,
        "extraction_status": "pending_review",
    }

    result = validate_extracted_fact(fact_data, source_text)

    assert result["fact_type"] == "required_document"
    assert result["evidence_locator"]["quoted_text"] in source_text
    assert result["extraction_status"] == "pending_review"


def test_validate_extracted_fact_rejects_missing_excerpt():
    fact_data = {
        "source_snapshot_id": "11111111-1111-4111-8111-111111111111",
        "fact_key": "required_document:deadbeef",
        "fact_type": "required_document",
        "value": {"text": "This is a valid fact.", "language": "en"},
        "language": "en",
        "evidence_locator": {"quoted_text": "Not present in the source text"},
        "extraction_confidence": 0.75,
        "extraction_status": "pending_review",
    }

    with pytest.raises(ValueError):
        validate_extracted_fact(fact_data, "Completely different content.")


def test_identify_duplicate_reason_matches_exact_duplicate():
    reason, similarity = identify_duplicate_reason(
        "Applicants must submit proof of identity.",
        "Applicants must submit proof of identity.",
    )

    assert reason == "exact_duplicate"
    assert similarity == 1.0


def test_service_version_requires_verified_facts():
    version = SimpleNamespace(
        effective_from=date.today(),
        effective_to=None,
        fact_links=[SimpleNamespace(source_fact=SimpleNamespace(extraction_status="rejected"))],
    )

    with pytest.raises(ValueError):
        validate_service_version_for_publication(version)
