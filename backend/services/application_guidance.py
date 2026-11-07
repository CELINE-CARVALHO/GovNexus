"""Source-backed application guidance.

GovNexus prepares a citizen for an official application. It does not
submit one, and it only explains fields that a stored source actually lists.
"""

from __future__ import annotations

import re
from typing import Any

from backend.services.conversation_language import append_retrieval_aliases
from backend.services.demo_knowledge import VERIFICATION_LABEL, demo_items
from backend.services.document_guidance import UNAVAILABLE_MESSAGE, build_document_guidance

SENSITIVE_PATTERN = re.compile(
    r"\b(aadhaar|aadhar|uidai|pan\b|permanent account|bank account|ifsc|otp|one[- ]time password|password|cvv|card number)\b",
    re.IGNORECASE,
)
PORTAL_ONLY = "Complete securely on the official portal."
NOT_AVAILABLE = "Not available from the current source."
AFTER_APPLYING = (
    "Keep the application reference number if the official portal gives you one, "
    "and check the status on that portal. A processing time or approval date is "
    "not available from the stored record."
)


def looks_sensitive(value: str) -> bool:
    return bool(SENSITIVE_PATTERN.search(value or ""))


def reject_sensitive_answers(answers: dict[str, Any]) -> None:
    for key, value in (answers or {}).items():
        text = f"{key} {value}"
        if looks_sensitive(text):
            raise ValueError(
                "GovNexus does not collect Aadhaar, PAN, bank details, OTPs, or passwords. "
                "Enter those only on the official portal."
            )


def _https_url(value: str | None) -> str | None:
    if not value or not str(value).startswith("https://"):
        return None
    return str(value)


def build_guidance_packet(detail: dict[str, Any]) -> dict[str, Any]:
    service = detail.get("service") or {}
    official_url = _https_url(service.get("application_url") or service.get("official_url"))
    eligibility = list(detail.get("eligibility") or [])
    documents = list(detail.get("required_documents") or [])
    steps = list(detail.get("application_steps") or [])
    supplied_fields = list(detail.get("form_fields") or [])
    safe_fields = []
    portal_only = []
    for field in supplied_fields:
        label = str(field.get("official_label") or field.get("label") or "")
        if field.get("sensitive") or looks_sensitive(label):
            portal_only.append({
                "official_label": label or "Sensitive field",
                "instruction": PORTAL_ONLY,
            })
            continue
        safe_fields.append({
            "field_key": field.get("field_key") or label.lower().replace(" ", "_")[:80],
            "official_label": label,
            "explanation": field.get("plain_language_explanation") or field.get("explanation") or "",
            "required_status": field.get("required_status") or "unknown",
            "example": field.get("example") if field.get("example_from_source") else None,
        })
    post_submission = detail.get("post_submission") if isinstance(detail.get("post_submission"), dict) else None
    if post_submission is None:
        post_submission = {
            "acknowledgement": AFTER_APPLYING,
            "status_url": official_url,
            "timing_available": False,
        }
    category = (
        (service.get("category") or {}).get("name")
        if isinstance(service.get("category"), dict)
        else service.get("category")
    )
    document_pack = build_document_guidance(
        documents,
        category=str(category or ""),
        title=str(service.get("title") or ""),
    )
    verification = detail.get("verification_label") or (
        VERIFICATION_LABEL if detail.get("demo") else "Published service record."
    )
    stages = [
        {"id": "understand", "label": "Understand the scheme", "explanation": "Read what the stored record actually says about this scheme before you prepare an application.", "available": True},
        {"id": "eligibility", "label": "Check eligibility", "explanation": "Compare your situation with the conditions the source lists. This is not a government decision.", "available": True},
        {"id": "documents", "label": "Prepare documents", "explanation": "Confirmed documents are listed separately from preparation suggestions.", "available": True},
        {"id": "form", "label": "Understand the form", "explanation": "Field-by-field help is shown only when an official form field is stored. Sensitive fields stay on the official portal.", "available": True},
        {"id": "answers", "label": "Prepare answers", "explanation": "Draft only non-sensitive answers. Do not enter Aadhaar, PAN, bank account, OTP, or password.", "available": True},
        {"id": "review", "label": "Review readiness", "explanation": "Look over what is confirmed and what still needs the official portal before you leave GovNexus.", "available": True},
        {"id": "apply", "label": "Open the official portal", "explanation": "You submit the application yourself on the official portal. GovNexus does not submit it.", "available": True},
        {"id": "after", "label": "Understand what happens after applying", "explanation": AFTER_APPLYING, "available": True},
    ]
    return {
        "scheme_id": service.get("id"),
        "title": service.get("title") or service.get("code") or "Scheme",
        "verification_label": verification,
        "official_application_url": official_url,
        "submitted_by_govnexus": False,
        "approval_guaranteed": False,
        "description": service.get("description") or "",
        "category": category,
        "jurisdiction": (
            (detail.get("jurisdictions") or [{}])[0].get("location", {}).get("name")
            if detail.get("jurisdictions")
            else service.get("jurisdiction")
        ),
        "benefits": list(detail.get("benefits") or []),
        "eligibility": eligibility,
        "documents": documents,
        "document_guidance": document_pack,
        "steps": steps,
        "form_fields": safe_fields,
        "portal_only_fields": portal_only,
        "post_submission": post_submission,
        "stages": stages,
        "unavailable_message": NOT_AVAILABLE,
        "document_unavailable_message": UNAVAILABLE_MESSAGE,
        "draft_notice": (
            "A saved draft stays in this browser. It is not an official application "
            "and it has not been submitted."
        ),
    }


def catalogue_scheme(scheme_id: str) -> dict[str, Any] | None:
    from backend.services.demo_knowledge import DEMO_SERVICES

    return next((item for item in DEMO_SERVICES if item["id"] == scheme_id), None)


def assess_eligibility(conditions: list[dict[str, Any]], answers: dict[Any, Any] | None) -> list[dict[str, str]]:
    """Compare citizen answers with stored expected values. This is not an official decision."""
    provided = answers or {}
    results = []
    for index, item in enumerate(conditions or []):
        raw = provided.get(str(index), provided.get(index))
        answer = str(raw or "").strip().lower()
        expected = str(item.get("expected") or "").strip().lower()
        if answer not in {"yes", "no"} or not expected:
            status = "cannot_determine"
        elif answer == expected:
            status = "appears_satisfied"
        else:
            status = "not_satisfied"
        results.append({
            "index": str(index),
            "status": status,
            "prompt": item.get("prompt") or item.get("description") or "Documented condition",
        })
    return results


def active_scheme_from_question(question: str, history: list[str] | None = None) -> dict[str, Any] | None:
    retrieval = question_for_retrieval(question, history or [])
    matches = demo_items(retrieval)
    if not matches:
        return None
    item = matches[0]
    return {
        "id": item["id"],
        "title": item["title"],
        "official_url": item.get("official_url"),
        "verification_label": item.get("verification_label") or VERIFICATION_LABEL,
    }


def question_for_retrieval(
    message: str,
    history: list[str],
    stored_title: str | None = None,
    pinned_title: str | None = None,
) -> str:
    """Keep follow-ups on the active scheme and drop that scheme for a new topic."""
    from backend.modules.ai.retrieval.hybrid_retriever import query_terms

    message = append_retrieval_aliases(message)
    follow_up = re.compile(
        r"(document|documents|eligib\w*|apply|applying|benefit|benefits|this|that|those|"
        r"required|process|steps|\bit\b|where|second|condition|explain|kannada|hindi|"
        r"don't|do not|without|दस्तावे|पात्र|आवेदन|ದಾಖಲ|ಅರ್ಹ|ஆவண|தகுதி|పత్ర|అర్హత|"
        r"രേഖ|യോഗ്യത|कागद|নথি|દસ્તાવેજ|ਦਸਤਾਵੇਜ਼)",
        re.IGNORECASE,
    )
    current = demo_items(message)
    prior_title = pinned_title or stored_title
    prior_id = None
    if history:
        prior = demo_items(" ".join(history[-2:]))
        if prior:
            prior_title = prior[0]["title"]
            prior_id = prior[0]["id"]
    if pinned_title and not prior_id:
        prior_title = pinned_title
    weak_follow_up = bool(follow_up.search(message)) and len(query_terms(message)) < 5
    if current and prior_id and current[0]["id"] != prior_id and not weak_follow_up:
        return message
    if current and pinned_title and not history and not weak_follow_up:
        named = demo_items(message)
        if named and named[0]["title"] != pinned_title and len(query_terms(message)) >= 3:
            return message
    keep_context = bool(prior_title) and (
        bool(history) or bool(pinned_title)
    ) and (len(query_terms(message)) < 3 or follow_up.search(message) or not current)
    if keep_context:
        prefix = " ".join(part for part in [prior_title, *history[-2:]] if part)
        return f"{prefix} {message}".strip()[:800]
    return message
