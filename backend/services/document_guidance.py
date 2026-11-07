"""Separate confirmed scheme documents from preparation suggestions.

Confirmed items come only from a stored official record. Suggestions are
never labelled as mandatory requirements.
"""

from __future__ import annotations

import re
from typing import Any

AADHAAR_NOTE = (
    "Aadhaar may be requested for identity verification or benefit delivery. "
    "Check the scheme's official instructions for whether it is mandatory and "
    "whether an alternative is accepted."
)
UNAVAILABLE_MESSAGE = (
    "We could not confirm the complete document list for this scheme from the "
    "sources currently available. You can prepare commonly useful identity, "
    "address, and bank documents where relevant, but please check the official "
    "application portal for the exact requirements before applying."
)
COMMON_SECTION = "Commonly useful documents — confirm before applying."
PROGRESS_NOTE = (
    "Marking a document here only tracks your preparation. It does not mean "
    "the application is ready or that the authority will accept the document."
)

_AADHAAR = re.compile(r"\baadhaa?r\b", re.IGNORECASE)


def _suggestion(name: str, why: str) -> dict[str, Any]:
    return {
        "name": name,
        "why": why,
        "requirement": "confirm",
        "confirmed": False,
        "source_url": None,
        "alternatives": [],
    }


def _suggestions(context: str) -> list[dict[str, Any]]:
    text = (context or "").casefold()
    items = [
        _suggestion(
            "Aadhaar card or another accepted identity proof",
            AADHAAR_NOTE,
        ),
        _suggestion(
            "Proof of address",
            "Many application portals ask for an address proof. This is a preparation suggestion, not a confirmed requirement for this scheme.",
        ),
        _suggestion(
            "Bank passbook or another accepted bank-account proof",
            "Benefit payments are often sent to a bank account. Confirm the accepted proof on the official portal. Do not enter the account number here.",
        ),
        _suggestion(
            "Passport-size photograph",
            "Some forms ask for a photograph. Confirm the size and whether it is required.",
        ),
    ]
    if any(word in text for word in ("income", "pension", "welfare", "scholarship", "assistance")):
        items.append(_suggestion(
            "Income certificate, if the scheme uses an income condition",
            "Prepare this only if the official instructions use income as a condition.",
        ))
    if any(word in text for word in ("caste", "certificate", "nadakacheri")):
        items.append(_suggestion(
            "Caste certificate, if the scheme uses a social-category condition",
            "Prepare this only when the official instructions ask for a social-category proof.",
        ))
    if any(word in text for word in ("domicile", "residence", "resident")):
        items.append(_suggestion(
            "Residence or domicile certificate, if applicable",
            "Confirm whether this scheme asks for a residence or domicile proof.",
        ))
    if "disab" in text:
        items.append(_suggestion(
            "Disability certificate, if applicable",
            "Confirm the accepted disability certificate on the official instructions.",
        ))
    if any(word in text for word in ("agri", "farmer", "kisan", "land")):
        items.append(_suggestion(
            "Land or agricultural records, if the scheme is for landholding farmers",
            "Farmer schemes often refer to land records. Confirm the exact record on the official portal. This item is not a confirmed requirement unless a source lists it.",
        ))
    if any(word in text for word in ("educat", "scholar", "student", "college")):
        items.append(_suggestion(
            "Education certificates, if the scheme is for students",
            "Scholarship and education services often ask for study records. Confirm which certificates the portal lists.",
        ))
    return items


def build_document_guidance(
    documents: list[dict[str, Any]] | None,
    *,
    category: str = "",
    title: str = "",
) -> dict[str, Any]:
    confirmed: list[dict[str, Any]] = []
    for item in documents or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("document_code") or "").strip()
        if not name:
            continue
        mandatory = item.get("is_mandatory")
        if mandatory is False or item.get("conditional_rule"):
            requirement = "conditional"
        elif mandatory is True:
            requirement = "mandatory"
        else:
            requirement = "stated"
        alternatives = item.get("alternatives") or item.get("accepted_formats") or []
        if isinstance(alternatives, str):
            alternatives = [alternatives]
        why = item.get("why") or item.get("description") or "The stored source names this document."
        if _AADHAAR.search(name) and requirement != "mandatory":
            why = f"{why} {AADHAAR_NOTE}"
        confirmed.append({
            "name": name,
            "why": why,
            "requirement": requirement,
            "confirmed": True,
            "source_url": item.get("source_url"),
            "source_title": item.get("source_title"),
            "alternatives": [str(value) for value in alternatives if value],
        })

    aadhaar_confirmed = any(_AADHAAR.search(item["name"]) for item in confirmed)
    if confirmed:
        return {
            "status": "confirmed",
            "confirmed": confirmed,
            "commonly_useful": [],
            "section_title": None,
            "message": None,
            "aadhaar_note": None if aadhaar_confirmed else AADHAAR_NOTE,
            "progress_note": PROGRESS_NOTE,
        }
    return {
        "status": "incomplete",
        "confirmed": [],
        "commonly_useful": _suggestions(f"{category} {title}"),
        "section_title": COMMON_SECTION,
        "message": UNAVAILABLE_MESSAGE,
        "aadhaar_note": AADHAAR_NOTE,
        "progress_note": PROGRESS_NOTE,
    }
