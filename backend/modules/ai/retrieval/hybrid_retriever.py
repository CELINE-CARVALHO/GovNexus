from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import String, and_, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from backend.config import settings
from backend.database.models.category import Category, CategoryTranslation
from backend.database.models.department import Department, DepartmentTranslation
from backend.database.models.service import Service
from backend.database.models.service_version import ServiceTranslation, ServiceVersion
from backend.database.models.source import Source
from backend.database.models.source_fact import (
    ServiceFactLink,
    SourceFact,
    SourceFactTranslation,
    SourceSnapshot,
)
from backend.database.models.verification import FactVerification
from backend.modules.ai.llm.gemini_client import GeminiClient, GeminiProviderError


STOP_WORDS = {
    "a", "about", "after", "also", "an", "and", "are", "as", "at",
    "be", "by", "can", "do", "for", "from", "have", "how", "i", "in",
    "is", "it", "of", "on", "or", "the", "this", "to", "was", "we",
    "what", "when", "where", "which", "who", "why", "with", "you", "your",
}
SUPPORTED_APPROVALS = {"approved", "approve", "accepted", "accept"}


class PineconeProviderError(RuntimeError):
    pass


class VectorIndexConfigurationError(RuntimeError):
    pass


class PineconeClient:
    API_VERSION = "2026-07"
    NAMESPACE = "schemesathi"

    def __init__(
        self,
        api_key: str | None = None,
        index_host: str | None = None,
        index_name: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = settings.PINECONE_API_KEY if api_key is None else api_key
        self.index_host = (
            settings.PINECONE_INDEX_HOST if index_host is None else index_host
        )
        self.index_name = (
            settings.PINECONE_INDEX_NAME if index_name is None else index_name
        )
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.index_host and self.index_name)

    async def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        if not self.configured:
            raise PineconeProviderError("Pinecone is not configured.")
        payload = await self._request(
            "POST",
            "/query",
            json={
                "namespace": self.NAMESPACE,
                "vector": vector,
                "topK": top_k,
                "includeMetadata": True,
            },
        )
        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            raise PineconeProviderError("Pinecone returned malformed matches.")
        return [
            match
            for match in matches
            if isinstance(match, dict)
            and isinstance(match.get("id"), str)
            and isinstance(match.get("score"), (int, float))
            and math.isfinite(float(match["score"]))
        ]

    async def upsert(self, vectors: list[dict[str, Any]]) -> None:
        if not vectors:
            return
        await self._request(
            "POST",
            "/vectors/upsert",
            json={"namespace": self.NAMESPACE, "vectors": vectors},
        )

    async def delete(self, vector_ids: list[str]) -> None:
        if not vector_ids:
            return
        await self._request(
            "POST",
            "/vectors/delete",
            json={"namespace": self.NAMESPACE, "ids": vector_ids},
        )

    async def delete_facts(self, fact_ids: list[str]) -> None:
        if not fact_ids:
            return
        await self._request(
            "POST",
            "/vectors/delete",
            json={
                "namespace": self.NAMESPACE,
                "filter": {"fact_id": {"$in": fact_ids}},
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.configured:
            raise PineconeProviderError("Pinecone is not configured.")
        host = self.index_host.strip().rstrip("/")
        if not host.startswith("https://"):
            raise PineconeProviderError("Pinecone index host must use HTTPS.")
        try:
            async with httpx.AsyncClient(
                timeout=settings.GEMINI_TIMEOUT_SECONDS,
                transport=self.transport,
            ) as client:
                response = await client.request(
                    method,
                    f"{host}{path}",
                    headers={
                        "Api-Key": self.api_key,
                        "X-Pinecone-API-Version": self.API_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=json,
                )
        except httpx.RequestError as exc:
            raise PineconeProviderError(
                "Pinecone request failed."
            ) from exc
        if response.status_code >= 400:
            raise PineconeProviderError(
                f"Pinecone request failed with status {response.status_code}."
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise PineconeProviderError(
                "Pinecone returned invalid JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise PineconeProviderError("Pinecone returned an invalid response.")
        return payload


def query_terms(question: str) -> list[str]:
    tokens = re.findall(r"[^\W_]{2,}", question.casefold(), flags=re.UNICODE)
    return list(dict.fromkeys(token for token in tokens if token not in STOP_WORDS))[:12]


def _approved_fact_query(db: Session):
    snapshot_candidate = aliased(SourceSnapshot)
    verification_candidate = aliased(FactVerification)
    latest_verification_id = (
        select(verification_candidate.id)
        .where(verification_candidate.source_fact_id == SourceFact.id)
        .order_by(
            verification_candidate.verified_at.desc(),
            verification_candidate.created_at.desc(),
            verification_candidate.id.desc(),
        )
        .limit(1)
        .scalar_subquery()
    )
    latest_snapshot_id = (
        select(snapshot_candidate.id)
        .where(snapshot_candidate.source_id == SourceSnapshot.source_id)
        .order_by(snapshot_candidate.fetched_at.desc(), snapshot_candidate.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    eligible_service_link = exists(
        select(1)
        .select_from(ServiceFactLink)
        .join(
            ServiceVersion,
            ServiceVersion.id == ServiceFactLink.service_version_id,
        )
        .join(Service, Service.id == ServiceVersion.service_id)
        .where(
            ServiceFactLink.source_fact_id == SourceFact.id,
            ServiceVersion.publication_status == "published",
            or_(
                ServiceVersion.effective_from.is_(None),
                ServiceVersion.effective_from <= func.current_date(),
            ),
            or_(
                ServiceVersion.effective_to.is_(None),
                ServiceVersion.effective_to >= func.current_date(),
            ),
            Service.is_active.is_(True),
            Service.status == "active",
        )
    )
    has_service_link = exists(
        select(1).where(ServiceFactLink.source_fact_id == SourceFact.id)
    )
    return (
        db.query(SourceFact, SourceSnapshot, Source, FactVerification)
        .select_from(SourceFact)
        .join(
            SourceSnapshot,
            and_(
                SourceSnapshot.id == SourceFact.source_snapshot_id,
                SourceSnapshot.id == latest_snapshot_id,
            ),
        )
        .join(Source, Source.id == SourceSnapshot.source_id)
        .join(
            FactVerification,
            and_(
                FactVerification.source_fact_id == SourceFact.id,
                FactVerification.id == latest_verification_id,
            ),
        )
        .filter(
            SourceFact.extraction_status == "verified",
            func.lower(FactVerification.verification_status).in_(
                {"verified", *SUPPORTED_APPROVALS}
            ),
            func.lower(FactVerification.decision).in_(SUPPORTED_APPROVALS),
            Source.is_active.is_(True),
            func.lower(Source.authority_status).in_(
                {"official", "authoritative", "verified"}
            ),
            or_(~has_service_link, eligible_service_link),
        )
    )


def _translation_expression(language_code: str):
    return (
        select(SourceFactTranslation.translated_value)
        .where(
            SourceFactTranslation.source_fact_id == SourceFact.id,
            SourceFactTranslation.language_code == language_code,
            SourceFactTranslation.is_human_verified.is_(True),
        )
        .limit(1)
        .scalar_subquery()
    )


def _service_term_exists(term: str, language_code: str):
    service_version = aliased(ServiceVersion)
    service = aliased(Service)
    category = aliased(Category)
    department = aliased(Department)
    service_translation = aliased(ServiceTranslation)
    category_translation = aliased(CategoryTranslation)
    department_translation = aliased(DepartmentTranslation)
    pattern = f"%{term}%"
    return exists(
        select(1)
        .select_from(ServiceFactLink)
        .join(
            service_version,
            service_version.id == ServiceFactLink.service_version_id,
        )
        .join(service, service.id == service_version.service_id)
        .join(category, category.id == service.category_id)
        .join(department, department.id == service.department_id)
        .outerjoin(
            service_translation,
            and_(
                service_translation.service_version_id == service_version.id,
                service_translation.language_code.in_({language_code, "en"}),
            ),
        )
        .outerjoin(
            category_translation,
            and_(
                category_translation.category_id == category.id,
                category_translation.language_code.in_({language_code, "en"}),
            ),
        )
        .outerjoin(
            department_translation,
            and_(
                department_translation.department_id == department.id,
                department_translation.language_code.in_({language_code, "en"}),
            ),
        )
        .where(
            ServiceFactLink.source_fact_id == SourceFact.id,
            service_version.publication_status == "published",
            or_(
                service_version.effective_from.is_(None),
                service_version.effective_from <= func.current_date(),
            ),
            or_(
                service_version.effective_to.is_(None),
                service_version.effective_to >= func.current_date(),
            ),
            service.is_active.is_(True),
            service.status == "active",
            category.is_active.is_(True),
            department.is_active.is_(True),
            or_(
                service.code.ilike(pattern),
                service.slug.ilike(pattern),
                service_translation.title.ilike(pattern),
                service_translation.description.ilike(pattern),
                category.code.ilike(pattern),
                category_translation.name.ilike(pattern),
                category_translation.description.ilike(pattern),
                department.code.ilike(pattern),
                department_translation.name.ilike(pattern),
                department_translation.description.ilike(pattern),
            ),
        )
    )


def _service_context(
    db: Session,
    fact_ids: list[UUID],
    language_code: str,
) -> dict[str, dict[str, Any]]:
    if not fact_ids:
        return {}
    preferred_language = language_code.split("-", 1)[0].lower()
    service_title = (
        select(ServiceTranslation.title)
        .where(
            ServiceTranslation.service_version_id == ServiceVersion.id,
            ServiceTranslation.language_code.in_({preferred_language, "en"}),
        )
        .order_by(
            case(
                (ServiceTranslation.language_code == preferred_language, 0),
                else_=1,
            )
        )
        .limit(1)
        .scalar_subquery()
    )
    department_name = (
        select(DepartmentTranslation.name)
        .where(
            DepartmentTranslation.department_id == Department.id,
            DepartmentTranslation.language_code.in_({preferred_language, "en"}),
        )
        .order_by(
            case(
                (DepartmentTranslation.language_code == preferred_language, 0),
                else_=1,
            )
        )
        .limit(1)
        .scalar_subquery()
    )
    category_name = (
        select(CategoryTranslation.name)
        .where(
            CategoryTranslation.category_id == Category.id,
            CategoryTranslation.language_code.in_({preferred_language, "en"}),
        )
        .order_by(
            case(
                (CategoryTranslation.language_code == preferred_language, 0),
                else_=1,
            )
        )
        .limit(1)
        .scalar_subquery()
    )
    rows = (
        db.query(
            ServiceFactLink.source_fact_id,
            ServiceVersion.id,
            ServiceVersion.version_number,
            Service.code,
            Service.slug,
            Service.category_id,
            Category.code,
            category_name,
            Service.department_id,
            Department.code,
            department_name,
            service_title,
        )
        .join(
            ServiceVersion,
            ServiceVersion.id == ServiceFactLink.service_version_id,
        )
        .join(Service, Service.id == ServiceVersion.service_id)
        .join(Category, Category.id == Service.category_id)
        .join(Department, Department.id == Service.department_id)
        .filter(
            ServiceFactLink.source_fact_id.in_(fact_ids),
            ServiceVersion.publication_status == "published",
            or_(
                ServiceVersion.effective_from.is_(None),
                ServiceVersion.effective_from <= func.current_date(),
            ),
            or_(
                ServiceVersion.effective_to.is_(None),
                ServiceVersion.effective_to >= func.current_date(),
            ),
            Service.is_active.is_(True),
            Service.status == "active",
            Category.is_active.is_(True),
            Department.is_active.is_(True),
        )
        .order_by(ServiceVersion.version_number.desc())
        .all()
    )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result.setdefault(
            str(row[0]),
            {
                "service_version_id": str(row[1]),
                "service_version_number": row[2],
                "service_code": row[3],
                "service_name": row[11] or row[4],
                "service_slug": row[4],
                "category_id": str(row[5]),
                "category_code": row[6],
                "category_name": row[7] or row[6],
                "department_id": str(row[8]),
                "department_code": row[9],
                "department_name": row[10] or row[9],
                "title": row[11] or row[4],
            },
        )
    return result


def retrieve_eligible_facts(
    db: Session,
    *,
    question: str = "",
    language_code: str = "en",
    limit: int = 12,
    offset: int = 0,
    fact_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 100))
    query = _approved_fact_query(db)
    if fact_ids is not None:
        normalized_ids = []
        for value in fact_ids[:100]:
            try:
                normalized_ids.append(UUID(str(value)))
            except (TypeError, ValueError, AttributeError):
                continue
        if not normalized_ids:
            return []
        query = query.filter(SourceFact.id.in_(normalized_ids))

    terms = query_terms(question)
    lang = language_code.split("-", 1)[0].lower()
    translation = _translation_expression(lang)
    keyword_rank = None
    if terms:
        term_conditions = []
        for term in terms:
            pattern = f"%{term}%"
            term_conditions.append(
                or_(
                    SourceFact.fact_key.ilike(pattern),
                    SourceFact.fact_type.ilike(pattern),
                    cast(SourceFact.value_data, String).ilike(pattern),
                    translation.ilike(pattern),
                    Source.publisher_name.ilike(pattern),
                    _service_term_exists(term, lang),
                )
            )
        query = query.filter(or_(*term_conditions))
        keyword_rank = sum(
            (case((condition, 1), else_=0) for condition in term_conditions),
            start=0,
        )

    query = query.add_columns(translation.label("translated_text"))
    if keyword_rank is not None:
        query = query.order_by(keyword_rank.desc())
    rows = (
        query
        .order_by(FactVerification.verified_at.desc(), SourceFact.id.asc())
        .offset(max(0, offset))
        .limit(safe_limit)
        .all()
    )
    facts_by_id = {row[0].id for row in rows}
    service_info = _service_context(db, list(facts_by_id), lang)

    results = []
    for fact, snapshot, source, verification, translated_text in rows:
        value = fact.value_data or {}
        text = (
            translated_text
            or value.get("text")
            or ""
        )
        info = service_info.get(str(fact.id), {})
        normalized = " ".join(
            [
                text,
                fact.fact_key,
                fact.fact_type,
                source.publisher_name,
                info.get("service_code", ""),
                info.get("service_name", ""),
                info.get("category_code", ""),
                info.get("category_name", ""),
                info.get("department_code", ""),
                info.get("department_name", ""),
            ]
        ).casefold()
        score = (
            sum(1 for term in terms if term in normalized) / len(terms)
            if terms
            else 0.0
        )
        locator = fact.evidence_locator or {}
        results.append(
            {
                "fact_id": str(fact.id),
                "fact_ids": [str(fact.id)],
                "fact_key": fact.fact_key,
                "fact_type": fact.fact_type,
                "value": value,
                "text": text,
                "evidence_locator": locator,
                "publisher": source.publisher_name,
                "source_url": source.url,
                "source_type": source.source_type,
                "authority_status": source.authority_status,
                "source_snapshot_id": str(snapshot.id),
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
                "language": lang if translated_text else value.get("language", "en"),
                "translation_available": bool(translated_text),
                "keyword_score": float(score),
                "retrieval_methods": [],
                "service": info,
            }
        )
    return results


def _citation_reference(item: dict[str, Any]) -> dict[str, Any]:
    locator = item.get("evidence_locator") or {}
    service = item.get("service") or {}
    return {
        "fact_id": item["fact_id"],
        "publisher": item["publisher"],
        "url": item["source_url"],
        "source_snapshot_id": item["source_snapshot_id"],
        "service_name": service.get("service_name"),
        "evidence_excerpt": locator.get("quoted_text") or item.get("text", ""),
        "page_number": (
            locator.get("page_number")
            or locator.get("pdf_page")
            or locator.get("page")
        ),
        "section": locator.get("section") or locator.get("heading"),
    }


def merge_hybrid_results(
    keyword_results: list[dict[str, Any]],
    semantic_results: list[tuple[dict[str, Any], float]],
    *,
    limit: int,
    minimum_semantic_score: float,
    minimum_keyword_score: float = 0.0,
) -> list[dict[str, Any]]:
    accepted_keyword = [
        item
        for item in keyword_results
        if item["keyword_score"] >= minimum_keyword_score
    ]
    accepted_semantic = [
        (item, score)
        for item, score in semantic_results
        if score >= minimum_semantic_score
    ]
    merged: dict[str, dict[str, Any]] = {}
    keyword_ranks = {
        item["fact_id"]: rank
        for rank, item in enumerate(
            sorted(accepted_keyword, key=lambda row: row["keyword_score"], reverse=True),
            start=1,
        )
    }
    semantic_ranks = {
        item["fact_id"]: (rank, score)
        for rank, (item, score) in enumerate(
            sorted(accepted_semantic, key=lambda row: row[1], reverse=True),
            start=1,
        )
    }

    for item in [*accepted_keyword, *(entry[0] for entry in accepted_semantic)]:
        fact_id = item["fact_id"]
        row = merged.setdefault(fact_id, dict(item))
        row["retrieval_methods"] = []
        if fact_id in keyword_ranks:
            row["retrieval_methods"].append("keyword")
        if fact_id in semantic_ranks:
            row["retrieval_methods"].append("semantic")
            row["semantic_score"] = semantic_ranks[fact_id][1]
        keyword_rank = keyword_ranks.get(fact_id)
        semantic_rank = semantic_ranks.get(fact_id, (None, None))[0]
        row["hybrid_score"] = sum(
            1.0 / (60 + rank)
            for rank in (keyword_rank, semantic_rank)
            if rank is not None
        )
        row["retrieval_method"] = (
            "hybrid"
            if len(row["retrieval_methods"]) == 2
            else row["retrieval_methods"][0]
        )

    ranked = sorted(
        merged.values(),
        key=lambda item: (
            item["hybrid_score"],
            item.get("semantic_score", 0.0),
            item["keyword_score"],
        ),
        reverse=True,
    )

    collapsed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in ranked:
        item.setdefault("fact_ids", [item["fact_id"]])
        text_key = re.sub(r"\s+", " ", item.get("text", "").casefold()).strip()
        key = (
            item["fact_type"],
            str((item.get("service") or {}).get("service_version_id", "")),
            text_key,
        )
        existing = collapsed.get(key)
        if existing is None:
            item["supporting_sources"] = [_citation_reference(item)]
            collapsed[key] = item
        else:
            existing["supporting_sources"].append(_citation_reference(item))
            existing["fact_ids"].append(item["fact_id"])
    result = list(collapsed.values())[:max(1, min(int(limit), 50))]
    _mark_potential_conflicts(result)
    return result


def _mark_potential_conflicts(items: list[dict[str, Any]]) -> None:
    conflict_types = {"eligibility", "fee", "deadline"}
    by_service_type: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in items:
        service_id = (item.get("service") or {}).get("service_version_id")
        if service_id and item["fact_type"] in conflict_types:
            by_service_type[(service_id, item["fact_type"])].add(
                re.sub(r"\s+", " ", item["text"].casefold()).strip()
            )
    for item in items:
        service_id = (item.get("service") or {}).get("service_version_id")
        item["potential_conflict"] = bool(
            service_id
            and len(by_service_type.get((service_id, item["fact_type"]), set())) > 1
        )


async def retrieve_hybrid_facts(
    db: Session,
    question: str,
    language_code: str,
    *,
    limit: int | None = None,
    gemini: GeminiClient | None = None,
    pinecone: PineconeClient | None = None,
) -> tuple[list[dict[str, Any]], str]:
    result_limit = limit or settings.RAG_KEYWORD_LIMIT
    keyword_results = (
        retrieve_eligible_facts(
            db,
            question=question,
            language_code=language_code,
            limit=max(result_limit * 3, 12),
        )
        if query_terms(question)
        else []
    )
    gemini_client = gemini or GeminiClient()
    pinecone_client = pinecone or PineconeClient()
    semantic_results: list[tuple[dict[str, Any], float]] = []
    semantic_status = "not_configured"

    if pinecone_client.configured and gemini_client.api_key:
        try:
            vector = await gemini_client.embed(
                question,
                task_type="RETRIEVAL_QUERY",
            )
            matches = await pinecone_client.query(
                vector,
                top_k=max(1, min(settings.RAG_SEMANTIC_LIMIT, 100)),
            )
            scores: dict[str, float] = {}
            for match in matches:
                metadata = match.get("metadata")
                if not isinstance(metadata, dict):
                    continue
                fact_id = metadata.get("fact_id")
                try:
                    fact_id = str(UUID(str(fact_id)))
                except (TypeError, ValueError, AttributeError):
                    continue
                score = float(match["score"])
                if score >= settings.RAG_MIN_SEMANTIC_SCORE:
                    scores[fact_id] = max(score, scores.get(fact_id, float("-inf")))
            authoritative = retrieve_eligible_facts(
                db,
                language_code=language_code,
                limit=len(scores) or 1,
                fact_ids=list(scores),
            )
            semantic_results = [
                (item, scores[item["fact_id"]])
                for item in authoritative
                if item["fact_id"] in scores
            ]
            semantic_status = "available"
        except (GeminiProviderError, PineconeProviderError):
            semantic_status = "unavailable"
    elif not gemini_client.api_key:
        semantic_status = "unavailable"

    merged = merge_hybrid_results(
        keyword_results,
        semantic_results,
        limit=result_limit,
        minimum_semantic_score=settings.RAG_MIN_SEMANTIC_SCORE,
        minimum_keyword_score=settings.RAG_MIN_KEYWORD_SCORE,
    )
    return merged, semantic_status


async def sync_fact_vectors(
    db: Session,
    fact_ids: list[str],
    *,
    gemini: GeminiClient | None = None,
    pinecone: PineconeClient | None = None,
) -> dict[str, int]:
    gemini_client = gemini or GeminiClient()
    pinecone_client = pinecone or PineconeClient()
    if not gemini_client.api_key or not pinecone_client.configured:
        raise VectorIndexConfigurationError(
            "Gemini embeddings and Pinecone are required to sync vectors."
        )

    requested_ids = list(dict.fromkeys(fact_ids))[:100]
    eligible = retrieve_eligible_facts(
        db,
        language_code="en",
        limit=max(1, len(requested_ids)),
        fact_ids=requested_ids,
    )
    eligible_ids = {item["fact_id"] for item in eligible}
    stale_ids = [value for value in requested_ids if value not in eligible_ids]

    translations = (
        db.query(SourceFactTranslation)
        .filter(
            SourceFactTranslation.source_fact_id.in_(
                [UUID(fact_id) for fact_id in eligible_ids]
            ),
            SourceFactTranslation.is_human_verified.is_(True),
        )
        .all()
        if eligible_ids
        else []
    )
    translations_by_fact: dict[str, list[SourceFactTranslation]] = defaultdict(list)
    for translation in translations:
        translations_by_fact[str(translation.source_fact_id)].append(translation)

    documents: list[dict[str, Any]] = []
    for item in eligible:
        service = item.get("service") or {}
        base_language = str(item.get("language") or "en").split("-", 1)[0].lower()
        documents.append(
            {
                "fact_id": item["fact_id"],
                "text": item["text"],
                "language": base_language,
                "snapshot_id": item["source_snapshot_id"],
                "service_version_id": service.get("service_version_id"),
            }
        )
        for translation in translations_by_fact.get(item["fact_id"], []):
            documents.append(
                {
                    "fact_id": item["fact_id"],
                    "text": translation.translated_value,
                    "language": translation.language_code,
                    "snapshot_id": item["source_snapshot_id"],
                    "service_version_id": service.get("service_version_id"),
                }
            )

    vectors: list[dict[str, Any]] = []
    for offset in range(0, len(documents), 100):
        batch = documents[offset : offset + 100]
        embeddings = await gemini_client.embed_many(
            [document["text"] for document in batch],
            task_type="RETRIEVAL_DOCUMENT",
        )
        for document, embedding in zip(batch, embeddings):
            vectors.append(
                {
                    "id": f"{document['fact_id']}:{document['language']}",
                    "values": embedding,
                    "metadata": {
                        "fact_id": document["fact_id"],
                        "source_snapshot_id": document["snapshot_id"],
                        "service_version_id": document["service_version_id"],
                        "language": document["language"],
                    },
                }
            )
    if stale_ids:
        await pinecone_client.delete_facts(stale_ids)
    for offset in range(0, len(vectors), 100):
        await pinecone_client.upsert(vectors[offset : offset + 100])
    return {"upserted": len(vectors), "deleted": len(stale_ids)}