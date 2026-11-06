from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from backend.database.connection import get_db
from backend.database.models.category import Category
from backend.database.models.location import Location
from backend.services.demo_knowledge import DEMO_SERVICES, demo_items


router = APIRouter(prefix="/demo", tags=["Local demonstration catalogue"])


def _category_code(db: Session, category_id: str | None) -> str:
    if not category_id:
        return ""
    try:
        normalized_id = UUID(category_id)
    except (TypeError, ValueError):
        return ""
    category = db.query(Category).filter(Category.id == normalized_id).first()
    return category.code if category else ""


def _jurisdiction_code(db: Session, location_id: str | None) -> str:
    if not location_id:
        return ""
    try:
        normalized_id = UUID(location_id)
    except (TypeError, ValueError):
        return ""
    location = db.query(Location).filter(Location.id == normalized_id).first()
    return location.code if location else ""


def _list_item(item: dict) -> dict:
    return {
        "id": item["id"],
        "code": item["code"],
        "slug": item["id"],
        "title": item["title"],
        "description": item["description"],
        "application_url": item["official_url"],
        "category": {"code": item["category_code"], "name": item["category"]},
        "jurisdiction": item["jurisdiction"],
        "publisher": item["publisher"],
        "demo": True,
        "checked_on": item["checked_on"],
        "verification_label": item.get("verification_label"),
        "jurisdiction_code": item["jurisdiction_code"],
    }


@router.get("/services")
def list_demo_services(
    search: str = Query(default="", max_length=150),
    category_id: str | None = None,
    state_id: str | None = None,
    jurisdiction_code: str = Query(default="", max_length=32),
    level: str = Query(default="", max_length=16),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    jurisdiction = jurisdiction_code or _jurisdiction_code(db, state_id)
    if level not in {"", "central", "state", "all"}:
        raise HTTPException(status_code=422, detail="Unknown coverage filter.")
    items = demo_items(
        search,
        category=_category_code(db, category_id),
        jurisdiction=jurisdiction,
        level="" if level == "all" else level,
    )
    total = len(items)
    start = (page - 1) * limit
    page_items = items[start : start + limit]
    pages = max(1, (total + limit - 1) // limit)
    return {
        "items": [_list_item(item) for item in page_items],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": pages},
        "demo": True,
        "notice": (
            "AI-researched demo information — not yet human-verified. "
            "Confirm current details on the linked government page."
        ),
    }


@router.get("/jurisdictions")
def list_demo_jurisdictions():
    from backend.master_data import INDIAN_SUBDIVISIONS

    return {
        "central": {"code": "IN", "name": "Central Government", "type": "central"},
        "items": [
            {"code": code, "type": kind, "name": name}
            for code, kind, name in INDIAN_SUBDIVISIONS
        ],
    }


@router.get("/services/{service_id}")
def get_demo_service(service_id: str):
    item = next((value for value in DEMO_SERVICES if value["id"] == service_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Demonstration service not found")
    details = item["details"]
    return {
        "demo": True,
        "service": {
            **_list_item({**item, "checked_on": item.get("checked_on") or "2026-11-06"}),
            "department": {"name": item["publisher"], "website_url": item["official_url"]},
        },
        "jurisdictions": [{"location": {"name": item["jurisdiction"]}}],
        "version": {"number": "demo", "effective_from": None, "change_summary": "Local demonstration record; not a published service version."},
        "eligibility": details["eligibility"],
        "benefits": details.get("benefits", []),
        "required_documents": details["documents"],
        "application_steps": details["steps"],
        "verification_label": item.get("verification_label") or "AI-researched demo information — not yet human-verified.",
        "checked_on": item.get("checked_on"),
        "evidence": {"items": [{"relationship_type": "general_information", "source": {"publisher": item["publisher"], "url": item["official_url"], "authority_status": "official source link; demo record"}, "value": item["evidence"]}]},
        "disclaimer": (
            f"{item.get('verification_label') or 'AI-researched demo information — not yet human-verified.'} "
            f"Source checked on {item.get('checked_on') or '2026-11-06'}. "
            "This is not a published production service record. Confirm current details on the linked government portal."
        ),
    }
