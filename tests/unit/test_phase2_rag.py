from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.v1 import chat
from backend.database.base import Base
from backend.database.models.category import Category
from backend.database.models.department import Department
from backend.database.models.language import Language
from backend.database.models.service import Service
from backend.database.models.service_version import ServiceVersion
from backend.database.models.source import Source
from backend.database.models.source_fact import (
    ServiceFactLink,
    SourceFact,
    SourceFactTranslation,
    SourceSnapshot,
)
from backend.database.models.verification import FactVerification
from backend.modules.ai.llm.gemini_client import (
    GeminiClient,
    GeminiProviderError,
)
from backend.modules.ai.retrieval.hybrid_retriever import (
    PineconeClient,
    PineconeProviderError,
    PineconeProviderError,
    merge_hybrid_results,
    retrieve_eligible_facts,
    retrieve_hybrid_facts,
    sync_fact_vectors,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    session = test_session()
    session.add_all(
        [
            Language(code="en", english_name="English", native_name="English", is_active=True),
            Language(code="hi", english_name="Hindi", native_name="हिन्दी", is_active=True),
        ]
    )
    department = Department(code="TEST-DEPT", level="central", is_active=True)
    category = Category(code="TEST-CATEGORY", is_active=True)
    session.add_all([department, category])
    session.flush()
    service = Service(
        code="TEST-SERVICE",
        slug="test-service",
        department_id=department.id,
        category_id=category.id,
        status="active",
        is_active=True,
    )
    source = Source(
        url="https://example.gov.in/service",
        url_hash="a" * 64,
        publisher_name="Example Government",
        source_type="government",
        authority_status="official",
        retrieval_interval_hours=24,
        is_active=True,
    )
    session.add_all([service, source])
    session.flush()
    snapshot = SourceSnapshot(
        source_id=source.id,
        fetched_at=datetime.utcnow(),
        content_hash="b" * 64,
        content_type="text/html",
        http_status=200,
        storage_uri="data/source_snapshots/test/page.html",
        extraction_status="completed",
        extracted_at=datetime.utcnow(),
    )
    session.add(snapshot)
    session.flush()
    version = ServiceVersion(
        service_id=service.id,
        version_number=1,
        effective_from=date.today() - timedelta(days=1),
        effective_to=date.today() + timedelta(days=30),
        publication_status="published",
    )
    session.add(version)
    session.flush()
    session.info["source"] = source
    session.info["snapshot"] = snapshot
    session.info["service"] = service
    session.info["version"] = version
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def add_fact(
    db: Session,
    text: str,
    *,
    extraction_status: str = "verified",
    decision: str = "approved",
    verification_status: str = "approved",
    linked: bool = True,
) -> SourceFact:
    fact = SourceFact(
        source_snapshot_id=db.info["snapshot"].id,
        fact_key=f"eligibility:{uuid4().hex}",
        fact_type="eligibility",
        value_data={"text": text, "language": "en"},
        evidence_locator={
            "quoted_text": text,
            "page_number": 2,
            "section": "Eligibility",
        },
        extraction_confidence=0.95,
        extraction_status=extraction_status,
    )
    db.add(fact)
    db.flush()
    db.add(
        FactVerification(
            source_fact_id=fact.id,
            verification_status=verification_status,
            decision=decision,
            verified_at=datetime.utcnow(),
        )
    )
    if linked:
        db.add(
            ServiceFactLink(
                service_version_id=db.info["version"].id,
                source_fact_id=fact.id,
                relationship_type="eligibility",
            )
        )
    db.commit()
    return fact


def test_keyword_retrieval_requires_latest_approved_verified_fact(db):
    approved = add_fact(db, "Applicants must be over 18 years old.")
    pending = add_fact(
        db,
        "Applicants must be under 25 years old.",
        extraction_status="pending_review",
    )
    rejected = add_fact(
        db,
        "Applicants must be under 40 years old.",
        extraction_status="rejected",
        decision="rejected",
        verification_status="rejected",
    )

    rows = retrieve_eligible_facts(
        db,
        question="Applicants over 18",
        language_code="en",
    )

    assert [row["fact_id"] for row in rows] == [str(approved.id)]
    assert str(pending.id) not in {row["fact_id"] for row in rows}
    assert str(rejected.id) not in {row["fact_id"] for row in rows}


def test_keyword_retrieval_supports_bounded_pagination(db):
    add_fact(db, "Applicants must provide an income certificate.")
    add_fact(db, "Applicants must provide a bank account.")
    add_fact(db, "Applicants must provide proof of identity.")

    page_one = retrieve_eligible_facts(
        db,
        question="Applicants must provide",
        language_code="en",
        limit=1,
        offset=0,
    )
    page_two = retrieve_eligible_facts(
        db,
        question="Applicants must provide",
        language_code="en",
        limit=1,
        offset=1,
    )

    assert len(page_one) == len(page_two) == 1
    assert page_one[0]["fact_id"] != page_two[0]["fact_id"]


def test_keyword_retrieval_rejects_latest_non_approved_decision(db):
    fact = add_fact(db, "The annual income limit is 200000 rupees.")
    db.add(
        FactVerification(
            source_fact_id=fact.id,
            verification_status="needs_revision",
            decision="needs_revision",
            verified_at=datetime.utcnow() + timedelta(seconds=1),
        )
    )
    db.commit()

    rows = retrieve_eligible_facts(
        db,
        question="annual income limit",
        language_code="en",
    )

    assert rows == []


def test_retrieval_excludes_facts_from_superseded_source_snapshots(db):
    fact = add_fact(db, "Applicants must provide a current income certificate.")
    newer_snapshot = SourceSnapshot(
        source_id=db.info["source"].id,
        fetched_at=datetime.utcnow() + timedelta(seconds=2),
        content_hash="c" * 64,
        content_type="text/html",
        http_status=200,
        storage_uri="data/source_snapshots/test/newer.html",
        extraction_status="completed",
    )
    db.add(newer_snapshot)
    db.commit()

    rows = retrieve_eligible_facts(
        db,
        question="income certificate",
        language_code="en",
    )

    assert rows == []
    assert fact.id is not None


def test_retrieval_excludes_expired_published_service_version(db):
    fact = add_fact(db, "Applicants must be at least 18 years old.")
    version = db.info["version"]
    version.effective_to = date.today() - timedelta(days=1)
    db.commit()

    rows = retrieve_eligible_facts(
        db,
        question="at least 18 years old",
        language_code="en",
    )

    assert rows == []
    assert fact.id is not None


def test_keyword_retrieval_includes_published_service_category_and_department(db):
    fact = add_fact(db, "Applicants must be at least 18 years old.")

    rows = retrieve_eligible_facts(
        db,
        question="TEST-CATEGORY",
        language_code="en",
    )

    assert rows[0]["fact_id"] == str(fact.id)
    assert rows[0]["service"]["category_code"] == "TEST-CATEGORY"
    assert rows[0]["service"]["department_code"] == "TEST-DEPT"


def test_hybrid_merge_deduplicates_same_fact_and_repeated_text():
    first = {
        "fact_id": "fact-a",
        "fact_type": "fee",
        "text": "The application fee is 100 rupees.",
        "keyword_score": 2.0,
        "service": {"service_version_id": "version-a"},
        "publisher": "Gov A",
        "source_url": "https://a.gov.in",
        "source_snapshot_id": "snapshot-a",
        "evidence_locator": {"quoted_text": "The application fee is 100 rupees."},
    }
    second = {
        **first,
        "fact_id": "fact-b",
        "publisher": "Gov B",
        "source_url": "https://b.gov.in",
        "source_snapshot_id": "snapshot-b",
    }

    result = merge_hybrid_results(
        [first, second],
        [(first, 0.9)],
        limit=10,
        minimum_semantic_score=0.3,
    )

    assert len(result) == 1
    assert result[0]["fact_ids"] == ["fact-a", "fact-b"]
    assert len(result[0]["supporting_sources"]) == 2
    assert result[0]["retrieval_method"] == "hybrid"


def test_semantic_ids_are_revalidated_against_mysql(db):
    add_fact(db, "Applicants must submit proof of identity.")
    rejected = add_fact(
        db,
        "Applicants must submit proof of address.",
        extraction_status="rejected",
        decision="rejected",
        verification_status="rejected",
    )

    class FakeGemini:
        api_key = "configured"

        async def embed(self, text, *, task_type):
            return [0.1, 0.2]

    class FakePinecone:
        configured = True

        async def query(self, vector, top_k):
            return [
                {
                    "id": f"{rejected.id}:en",
                    "score": 0.99,
                    "metadata": {"fact_id": str(rejected.id)},
                }
            ]

    rows, semantic_status = asyncio.run(
        retrieve_hybrid_facts(
            db,
            "a query without matching verified words",
            "en",
            gemini=FakeGemini(),
            pinecone=FakePinecone(),
        )
    )

    assert rows == []
    assert semantic_status == "available"


def test_keyword_only_fallback_reports_pinecone_unconfigured(db):
    fact = add_fact(db, "Applicants need a bank account.")

    class NoPinecone:
        configured = False

    class NoGemini:
        api_key = ""

    rows, semantic_status = asyncio.run(
        retrieve_hybrid_facts(
            db,
            "bank account",
            "en",
            gemini=NoGemini(),
            pinecone=NoPinecone(),
        )
    )

    assert rows[0]["fact_id"] == str(fact.id)
    assert rows[0]["retrieval_method"] == "keyword"
    assert semantic_status == "unavailable"


def test_pinecone_failure_falls_back_to_relevant_keyword_results(db):
    fact = add_fact(db, "Applicants must provide an income certificate.")

    class FakeGemini:
        api_key = "configured"

        async def embed(self, text, *, task_type):
            return [0.1, 0.2]

    class FailedPinecone:
        configured = True

        async def query(self, vector, top_k):
            raise PineconeProviderError("private connection details")

    rows, semantic_status = asyncio.run(
        retrieve_hybrid_facts(
            db,
            "income certificate",
            "en",
            gemini=FakeGemini(),
            pinecone=FailedPinecone(),
        )
    )

    assert [row["fact_id"] for row in rows] == [str(fact.id)]
    assert rows[0]["retrieval_method"] == "keyword"
    assert semantic_status == "unavailable"


def test_no_evidence_does_not_call_gemini(monkeypatch, db):
    async def no_evidence(*args, **kwargs):
        return [], "not_configured"

    async def should_not_generate(*args, **kwargs):
        raise AssertionError("Gemini must not run without eligible evidence.")

    monkeypatch.setattr(chat, "retrieve_hybrid_facts", no_evidence)
    monkeypatch.setattr(chat, "generate_grounded_answer", should_not_generate)
    response = asyncio.run(
        chat.send_chat_message(
            chat.ChatRequest(message="What is my benefit?", language_code="en"),
            db,
        )
    )

    assert response.evidence_found is False
    assert response.citations == []
    assert "could not find" in response.answer.lower()


def test_generated_answer_cannot_cite_fact_outside_context():
    class FakeGemini:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            return "The fee is 100 rupees. [S2]"

    evidence = [
        {
            "text": "The fee is 100 rupees.",
            "fact_type": "fee",
            "sources": [
                {
                    "citation_marker": "[S1]",
                    "publisher": "Gov",
                    "url": "https://example.gov.in",
                    "fact_id": "fact-a",
                }
            ],
        }
    ]

    answer = asyncio.run(
        chat.generate_grounded_answer(
            "What is the fee?",
            "en",
            evidence,
            client=FakeGemini(),
        )
    )

    assert "[S2]" not in answer
    assert "[S1]" in answer


def test_uncited_claims_are_replaced_with_supported_excerpts():
    class FakeGemini:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            return "The fee is 100 rupees. [S1] You can apply online."

    evidence = [
        {
            "text": "The application fee is 100 rupees.",
            "fact_type": "fee",
            "sources": [
                {
                    "citation_marker": "[S1]",
                    "publisher": "Gov",
                    "url": "https://example.gov.in",
                    "fact_id": "fact-a",
                }
            ],
        }
    ]

    answer = asyncio.run(
        chat.generate_grounded_answer(
            "What is the fee?",
            "en",
            evidence,
            client=FakeGemini(),
        )
    )

    assert "You can apply online" not in answer
    assert "The application fee is 100 rupees." in answer


def test_malformed_gemini_response_is_rejected():
    async def handler(request):
        return httpx.Response(200, json={"candidates": []})

    client = GeminiClient(
        api_key="test-key",
        model="gemini-test",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeminiProviderError, match="malformed"):
        asyncio.run(client.generate("rules", "question"))


def test_pinecone_client_uses_configured_https_host_and_version():
    async def handler(request):
        assert request.url.host == "index.example.pinecone.io"
        assert request.url.path == "/query"
        assert request.headers["Api-Key"] == "test-key"
        assert request.headers["X-Pinecone-API-Version"] == "2026-07"
        return httpx.Response(
            200,
            json={
                "matches": [
                    {
                        "id": "fact-id:en",
                        "score": 0.8,
                        "metadata": {"fact_id": "fact-id"},
                    }
                ]
            },
        )

    client = PineconeClient(
        api_key="test-key",
        index_host="https://index.example.pinecone.io",
        index_name="scheme-facts",
        transport=httpx.MockTransport(handler),
    )
    matches = asyncio.run(client.query([0.1, 0.2], top_k=5))

    assert matches[0]["id"] == "fact-id:en"
    assert matches[0]["score"] == 0.8


def test_conversation_id_is_bound_to_guest_session(db):
    first = chat.ChatRequest(message="Question one", language_code="en")
    second = chat.ChatRequest(message="Question two", language_code="en")
    first_conversation, first_token, _ = chat._resolve_conversation(db, first)
    _, second_token, _ = chat._resolve_conversation(db, second)
    db.commit()

    with pytest.raises(HTTPException) as error:
        chat._resolve_conversation(
            db,
            chat.ChatRequest(
                message="Question three",
                language_code="en",
                conversation_id=first_conversation.id,
                guest_session_token=second_token,
            ),
        )

    assert error.value.status_code == 404
    assert first_token


def test_gemini_provider_failure_returns_safe_api_error():
    class FailedGemini:
        configured = True

        async def generate(self, system_instruction, user_prompt):
            raise GeminiProviderError("private provider details", retryable=True)

    evidence = [
        {
            "text": "Official excerpt.",
            "fact_type": "service_information",
            "sources": [
                {
                    "citation_marker": "[S1]",
                    "publisher": "Gov",
                    "url": "https://example.gov.in",
                    "fact_id": "fact-a",
                }
            ],
        }
    ]
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            chat.generate_grounded_answer(
                "Question",
                "en",
                evidence,
                client=FailedGemini(),
            )
        )
    assert error.value.status_code == 503
    assert "private provider details" not in error.value.detail


def test_verified_human_translation_is_used_for_multilingual_query(db):
    fact = add_fact(db, "Applicants must submit proof of identity.")
    db.add(
        SourceFactTranslation(
            source_fact_id=fact.id,
            language_code="hi",
            translated_value="पहचान का प्रमाण जमा करना आवश्यक है।",
            translation_status="verified",
            is_human_verified=True,
        )
    )
    db.commit()

    rows = retrieve_eligible_facts(
        db,
        question="पहचान प्रमाण",
        language_code="hi-IN",
    )

    assert rows[0]["fact_id"] == str(fact.id)
    assert rows[0]["translation_available"] is True
    assert rows[0]["language"] == "hi"


def test_vector_sync_updates_eligible_and_deletes_ineligible(db):
    eligible = add_fact(db, "Eligible fact text.")
    rejected = add_fact(
        db,
        "Rejected fact text.",
        extraction_status="rejected",
        decision="rejected",
        verification_status="rejected",
    )

    class FakeGemini:
        api_key = "configured"

        async def embed_many(self, texts, *, task_type):
            assert task_type == "RETRIEVAL_DOCUMENT"
            return [[0.1, 0.2] for _ in texts]

    class FakePinecone:
        configured = True
        upserted = []
        deleted = []

        async def upsert(self, vectors):
            self.upserted.extend(vectors)

        async def delete_facts(self, fact_ids):
            self.deleted.extend(fact_ids)

    pinecone = FakePinecone()
    result = asyncio.run(
        sync_fact_vectors(
            db,
            [str(eligible.id), str(rejected.id)],
            gemini=FakeGemini(),
            pinecone=pinecone,
        )
    )

    assert result == {"upserted": 1, "deleted": 1}
    assert pinecone.upserted[0]["id"] == f"{eligible.id}:en"
    assert pinecone.upserted[0]["metadata"]["source_snapshot_id"]
    assert pinecone.deleted == [str(rejected.id)]
