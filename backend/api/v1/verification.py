from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models.source_fact import SourceFact
from backend.database.models.verification import (
    FactDuplicateCandidate,
    FactVerification,
    ReviewTask,
    FactReclassification,
)
from backend.database.models.administration import AdminUser
from backend.core.security import get_current_admin


router = APIRouter(
    prefix="/verification",
    tags=["Fact Verification"],
)


# ---------------------------------------------------------
# Request schemas
# ---------------------------------------------------------

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


class ReclassificationRequest(BaseModel):
    new_fact_type: str = Field(min_length=2, max_length=60)
    reason: str = Field(min_length=10, max_length=1000)


class DuplicateSuggestionReview(BaseModel):
    decision: str = Field(default="dismissed")
    notes: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------
# Review queue
# ---------------------------------------------------------

@router.get("/queue")
def get_review_queue(
    status: str = Query("open"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    tasks = (
        db.query(ReviewTask)
        .filter(ReviewTask.status == status)
        .order_by(ReviewTask.created_at.asc())
        .limit(limit)
        .all()
    )

    results = []

    for task in tasks:
        fact = db.query(SourceFact).filter(
            SourceFact.id == task.source_fact_id
        ).first()

        if not fact:
            continue

        value = fact.value_data or {}

        results.append({
            "task_id": str(task.id),
            "fact_id": str(fact.id),
            "task_status": task.status,
            "priority": task.priority,
            "fact_type": fact.fact_type,
            "text": value.get("text", ""),
            "language": value.get("language", "en"),
            "evidence": fact.evidence_locator,
        })

    return {"total": len(results), "items": results}


@router.get("/duplicate-suggestions")
def list_duplicate_suggestions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    rows = (
        db.query(FactDuplicateCandidate)
        .order_by(FactDuplicateCandidate.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "total": len(rows),
        "items": [
            {
                "id": str(item.id),
                "source_fact_id": str(item.source_fact_id),
                "duplicate_fact_id": str(item.duplicate_fact_id),
                "similarity_score": item.similarity_score,
                "reason": item.reason,
                "review_status": item.review_status,
                "notes": item.notes,
            }
            for item in rows
        ],
    }


@router.post("/{suggestion_id}/duplicate-review")
def review_duplicate_suggestion(
    suggestion_id: UUID,
    payload: DuplicateSuggestionReview,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    decision = payload.decision.strip().lower()
    if decision not in {"accepted", "dismissed"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be accepted or dismissed.",
        )

    suggestion = db.query(FactDuplicateCandidate).filter(FactDuplicateCandidate.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Duplicate suggestion not found.")

    suggestion.review_status = decision
    suggestion.reviewed_by_admin_id = current_admin.id
    suggestion.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    suggestion.notes = payload.notes or suggestion.notes

    db.commit()
    return {
        "message": "Duplicate suggestion reviewed.",
        "suggestion_id": str(suggestion.id),
        "decision": decision,
    }


# ---------------------------------------------------------
# Fact reclassification
# ---------------------------------------------------------

@router.post("/{fact_id}/reclassify")
def reclassify_fact(
    fact_id: UUID,
    payload: ReclassificationRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    new_type = payload.new_fact_type.strip().lower()
    reason = payload.reason.strip()

    if new_type not in ALLOWED_FACT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Unsupported fact classification.",
                "allowed_types": sorted(ALLOWED_FACT_TYPES),
            },
        )

    if len(reason) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide a meaningful reason of at least 10 characters.",
        )

    fact = db.query(SourceFact).filter(
        SourceFact.id == fact_id
    ).with_for_update().first()

    if fact is None:
        raise HTTPException(
            status_code=404,
            detail="Fact not found.",
        )

    # Reclassification must not silently change a final decision.
    if fact.extraction_status in {"verified", "rejected"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "This fact already has a final review status. "
                "A separate review workflow is required to reopen it."
            ),
        )

    if fact.extraction_status == "pending_review" and fact.fact_type == new_type:
        raise HTTPException(
            status_code=400,
            detail="The fact already has this classification.",
        )

    previous_type = fact.fact_type

    if previous_type == new_type:
        raise HTTPException(
            status_code=400,
            detail="The fact already has this classification.",
        )

    audit_record = FactReclassification(
        source_fact_id=fact.id,
        admin_id=current_admin.id,
        previous_fact_type=previous_type,
        new_fact_type=new_type,
        reason=reason,
    )

    try:
        db.add(audit_record)

        # Change classification only.
        # Do not approve or verify the fact.
        fact.fact_type = new_type

        # Ensure the fact remains pending review.
        fact.extraction_status = "pending_review"

        # Reopen any existing review task.
        tasks = db.query(ReviewTask).filter(
            ReviewTask.source_fact_id == fact.id,
            ReviewTask.status == "open",
        ).all()

        if not tasks:
            db.add(
                ReviewTask(
                    source_fact_id=fact.id,
                    task_type="fact_verification",
                    status="open",
                    priority="normal",
                )
            )

        db.commit()
        db.refresh(audit_record)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Fact reclassified successfully. Verification is still required.",
        "fact_id": str(fact.id),
        "previous_fact_type": previous_type,
        "new_fact_type": new_type,
        "extraction_status": fact.extraction_status,
        "audit_id": str(audit_record.id),
    }


# ---------------------------------------------------------
# Reclassification audit history
# ---------------------------------------------------------

@router.get("/{fact_id}/reclassification-history")
def get_reclassification_history(
    fact_id: UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    fact = db.query(SourceFact).filter(
        SourceFact.id == fact_id
    ).first()

    if fact is None:
        raise HTTPException(
            status_code=404,
            detail="Fact not found.",
        )

    records = (
        db.query(FactReclassification)
        .filter(FactReclassification.source_fact_id == fact_id)
        .order_by(FactReclassification.created_at.desc())
        .all()
    )

    return {
        "fact_id": str(fact_id),
        "total": len(records),
        "items": [
            {
                "audit_id": str(record.id),
                "admin_id": str(record.admin_id),
                "previous_fact_type": record.previous_fact_type,
                "new_fact_type": record.new_fact_type,
                "reason": record.reason,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ],
    }


# ---------------------------------------------------------
# Verification decision
# ---------------------------------------------------------

@router.post("/{fact_id}/decision")
def review_fact(
    fact_id: UUID,
    decision: str,
    notes: str = "",
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    allowed = {"approved", "rejected", "needs_revision"}

    if decision not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Decision must be one of: {', '.join(sorted(allowed))}",
        )

    fact = db.query(SourceFact).filter(
        SourceFact.id == fact_id
    ).first()

    if not fact:
        raise HTTPException(
            status_code=404,
            detail="Fact not found.",
        )

    if fact.extraction_status in {"verified", "rejected"}:
        raise HTTPException(
            status_code=409,
            detail="This fact already has a final verification record and cannot be overwritten.",
        )

    verification = FactVerification(
        source_fact_id=fact.id,
        verification_status=decision,
        decision=decision,
        notes=notes,
        reviewer_admin_id=current_admin.id,
    )

    db.add(verification)

    tasks = db.query(ReviewTask).filter(
        ReviewTask.source_fact_id == fact.id,
        ReviewTask.status == "open",
    ).all()

    for task in tasks:
        task.status = "completed"
        task.resolution = decision

    if decision == "approved":
        fact.extraction_status = "verified"
    elif decision == "rejected":
        fact.extraction_status = "rejected"
    else:
        fact.extraction_status = "pending_review"

    db.commit()

    return {
        "message": "Review decision saved",
        "fact_id": str(fact.id),
        "decision": decision,
    }
