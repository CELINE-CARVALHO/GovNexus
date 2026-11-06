from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.database.models import ReviewTask, Source, SourceFact, SourceSnapshot
from backend.services import fact_extraction


UIDAI_TEXT = """Registered Mobile Number
Registered mobile number is essential to access Aadhaar Online Services
You can verify your mobile number that has been declared at the time of enrolment.
If you have not registered your Mobile number while enrolling for Aadhaar, you are required to visit a Permanent Enrolment Centre to get it registered.

Age <5 years at the time of initial enrolment
-The child should be re-enroled when the child attains an age of 5 years and all biometric data should be provided.
Age between 5 and 15 years at the time of enrolment
- The Aadhaar number holder should furnish all biometrics for updates when he/she attains age of 15 years.
Age >15 years at the time of enrolment
- Aadhaar number holders are recommended to update their biometric data every 10 years.
Events like accidents or diseases leading to biometric exception
As the Aadhaar authentication service is becoming ubiquitous, Aadhaar number holders may also approach for biometric updates because of authentication failures.

Aadhaar details that can be updated are:
Demographic Information
Name, Address, Date of Birth/Age, Gender, Mobile Number, Email Address, Relationship Status and Information Sharing Consent
Biometric Information
Iris, Finger Prints and Facial Photograph

Modes of Update
1. Via Online
The online mode offers address update to the Aadhaar number holders where the Aadhaar number holder can directly place the address update request on the myAadhaar portal. The Aadhaar number holder needs to have mobile number registered with Aadhaar for using this service. The Aadhaar number holder is authenticated using sent OTP on his/her registered mobile number. To complete the update process, Aadhaar number holder needs to upload the
supporting POA documents
, which will be verified against requested data at a later stage by a quality and processing team.
By Visiting Aadhaar Enrolment Centre
Aadhaar number holders place the demographic/biometric update request with the help of an operator at an Aadhaar Enrolment Centre. In such a case, the documentary evidence is collected by the operator at the time of accepting the request. The document verification by the verifier also happens at the time of placing the update request. UIDAI currently has envisaged three modes for Assisted Updates:
a. Update Client Standard
"""


@pytest.fixture
def isolated_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_uidai_structured_candidates_preserve_supported_evidence_spans():
    candidates = fact_extraction.extract_fact_candidates(UIDAI_TEXT)

    assert {candidate["fact_type"] for candidate in candidates} >= {
        "service_information",
        "eligibility",
        "application_process",
        "required_document",
    }
    assert any(
        "Name, Address, Date of Birth/Age" in candidate["fact_text"]
        for candidate in candidates
    )
    assert any(
        "Iris, Finger Prints and Facial Photograph" in candidate["fact_text"]
        for candidate in candidates
    )
    assert any(
        candidate["fact_type"] == "service_information"
        and "authentication failures" in candidate["fact_text"]
        for candidate in candidates
    )
    assert any(
        "mobile number registered with Aadhaar" in candidate["fact_text"]
        and "OTP" in candidate["fact_text"]
        for candidate in candidates
    )
    assert any(
        candidate["fact_type"] == "required_document"
        and "supporting POA documents" in candidate["fact_text"]
        for candidate in candidates
    )
    assert any(
        candidate["fact_type"] == "application_process"
        and "Aadhaar Enrolment Centre" in candidate["fact_text"]
        and "documentary evidence" in candidate["fact_text"]
        for candidate in candidates
    )

    for candidate in candidates:
        assert (
            UIDAI_TEXT[
                candidate["character_start"] : candidate["character_end"]
            ]
            == candidate["quoted_text"]
        )


def test_age_rules_require_explicit_numeric_boundaries():
    candidates = fact_extraction.extract_fact_candidates(UIDAI_TEXT)
    age_facts = [
        candidate["fact_text"]
        for candidate in candidates
        if candidate["fact_type"] == "eligibility"
    ]

    assert len(age_facts) == 3
    assert any("Age <5 years" in fact for fact in age_facts)
    assert any("Age between 5 and 15 years" in fact for fact in age_facts)
    assert any("Age >15 years" in fact for fact in age_facts)
    assert not fact_extraction.extract_fact_candidates(
        "The service is available to residents and the page is informative."
    )


def test_headings_without_supporting_content_are_skipped():
    text = "Demographic Information\nBiometric Information\n"

    assert not fact_extraction.extract_fact_candidates(text)


def test_existing_sentence_rule_remains_compatible():
    text = "Applicants must submit proof of identity and proof of address."

    candidates = fact_extraction.extract_fact_candidates(text)

    assert len(candidates) == 1
    assert candidates[0]["fact_type"] == "required_document"
    assert candidates[0]["quoted_text"] == text


def test_extraction_creates_pending_facts_and_open_review_tasks_without_duplicates(
    isolated_db,
    tmp_path,
    monkeypatch,
):
    text_path = tmp_path / "uidai.txt"
    text_path.write_text(UIDAI_TEXT, encoding="utf-8")
    monkeypatch.setattr(
        fact_extraction,
        "resolve_snapshot_text_path",
        lambda storage_uri: text_path,
    )
    monkeypatch.setattr(fact_extraction, "PROJECT_ROOT", tmp_path)

    with isolated_db() as db:
        source = Source(
            url="https://uidai.gov.in/en/updating-data-on-aadhaar",
            url_hash="u" * 64,
            publisher_name="UIDAI",
            source_type="government",
            authority_status="official",
            is_active=True,
        )
        db.add(source)
        db.flush()
        snapshot = SourceSnapshot(
            source_id=source.id,
            fetched_at=datetime.utcnow(),
            content_hash="h" * 64,
            content_type="text/html",
            http_status=200,
            storage_uri="data/source_snapshots/test/uidai.html",
            extraction_status="completed",
            source=source,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        expected_count = len(fact_extraction.extract_fact_candidates(UIDAI_TEXT))
        first = fact_extraction.extract_snapshot_facts(db, snapshot)

        assert first["created"] == expected_count
        assert first["existing"] == 0
        facts = db.query(SourceFact).filter(
            SourceFact.source_snapshot_id == snapshot.id
        ).all()
        tasks = db.query(ReviewTask).filter(
            ReviewTask.source_fact_id.in_([fact.id for fact in facts])
        ).all()
        assert len(facts) == expected_count
        assert len(tasks) == expected_count
        assert all(fact.extraction_status == "pending_review" for fact in facts)
        assert all(fact.value_data["review_required"] is True for fact in facts)
        assert all(task.task_type == "fact_verification" for task in tasks)
        assert all(task.status == "open" for task in tasks)
        assert all(
            text_path.read_text(encoding="utf-8")[
                fact.evidence_locator["character_start"] : fact.evidence_locator[
                    "character_end"
                ]
            ]
            == fact.evidence_locator["quoted_text"]
            for fact in facts
        )

        second = fact_extraction.extract_snapshot_facts(db, snapshot)

        assert second["created"] == 0
        assert second["existing"] == expected_count
        assert db.query(SourceFact).count() == expected_count
        assert db.query(ReviewTask).count() == expected_count
