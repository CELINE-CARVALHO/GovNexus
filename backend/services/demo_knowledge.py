"""Read-only local demonstration knowledge.

This module is deliberately separate from SourceFact, verification, and
publication data.  Every item carries its official URL and the date checked.
It is suitable for a local demonstration only; it is not a publication path.
"""

from __future__ import annotations

from datetime import date
from typing import Any


DEMO_CHECKED_ON = date(2026, 11, 6).isoformat()


DEMO_SERVICES: list[dict[str, Any]] = [
    {
        "id": "demo-national-scholarship-portal",
        "title": "National Scholarship Portal",
        "code": "DEMO-NSP",
        "description": "The official National Scholarship Portal lists scholarship schemes and provides student access to scheme eligibility, applications, and status tools. Scheme-specific conditions and dates must be checked on the portal.",
        "category": "Education and scholarships",
        "category_code": "education",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "National Scholarship Portal",
        "official_url": "https://scholarships.gov.in/Students",
        "sources": [
            {"title": "NSP student portal", "url": "https://scholarships.gov.in/Students"},
            {"title": "NSP schemes", "url": "https://scholarships.gov.in/All-Scholarships"},
        ],
        "evidence": "The NSP student portal exposes scheme listings, scholarship eligibility, application, and status functions.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-aadhaar-enrolment-update",
        "title": "Aadhaar Enrolment and Update",
        "code": "DEMO-AADHAAR-UPDATE",
        "description": "UIDAI's official enrolment and update resources cover Aadhaar enrolment, updates, forms, guidelines, and related resident resources.",
        "category": "Aadhaar and identity",
        "category_code": "identity",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Unique Identification Authority of India (UIDAI)",
        "official_url": "https://uidai.gov.in/en/enrolment-and-updates",
        "sources": [{"title": "UIDAI Enrolment & Updates", "url": "https://uidai.gov.in/en/enrolment-and-updates"}],
        "evidence": "UIDAI describes this page as a place to access Aadhaar enrolment and update resources, forms, guidelines, and related documents.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-aadhaar-address-update",
        "title": "Aadhaar Address Update",
        "code": "DEMO-AADHAAR-ADDRESS",
        "description": "UIDAI's Aadhaar update guidance is the official starting point for checking the currently supported address-update routes and required evidence.",
        "category": "Aadhaar and identity",
        "category_code": "identity",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Unique Identification Authority of India (UIDAI)",
        "official_url": "https://uidai.gov.in/en/updating-data-on-aadhaar",
        "sources": [{"title": "UIDAI Updating Data on Aadhaar", "url": "https://uidai.gov.in/en/updating-data-on-aadhaar"}],
        "evidence": "The official UIDAI page explains that Aadhaar data should be kept accurate and up to date and presents update guidance.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-karnataka-caste-certificate",
        "title": "Karnataka Caste Certificate",
        "code": "DEMO-KA-CASTE-CERTIFICATE",
        "description": "Use Karnataka's Nadakacheri portal to check the current official route for caste-certificate services and requirements.",
        "category": "Certificates and documentation",
        "category_code": "certificates",
        "jurisdiction": "Karnataka",
        "jurisdiction_code": "IN-KA",
        "publisher": "Government of Karnataka — Nadakacheri",
        "official_url": "https://nadakacheri.karnataka.gov.in/",
        "sources": [{"title": "Nadakacheri official portal", "url": "https://nadakacheri.karnataka.gov.in/"}],
        "evidence": "The record identifies the official Karnataka portal to consult; service-specific requirements are not asserted here.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-karnataka-income-certificate",
        "title": "Karnataka Income Certificate",
        "code": "DEMO-KA-INCOME-CERTIFICATE",
        "description": "Use Karnataka's Nadakacheri portal to check the current official route for income-certificate services and requirements.",
        "category": "Certificates and documentation",
        "category_code": "certificates",
        "jurisdiction": "Karnataka",
        "jurisdiction_code": "IN-KA",
        "publisher": "Government of Karnataka — Nadakacheri",
        "official_url": "https://nadakacheri.karnataka.gov.in/",
        "sources": [{"title": "Nadakacheri official portal", "url": "https://nadakacheri.karnataka.gov.in/"}],
        "evidence": "The record identifies the official Karnataka portal to consult; service-specific requirements are not asserted here.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-seva-sindhu",
        "title": "Karnataka Seva Sindhu",
        "code": "DEMO-KA-SEVA-SINDHU",
        "description": "Seva Sindhu is Karnataka's official citizen-services portal. Use it to locate the current service route and instructions for a specific service.",
        "category": "Citizen services",
        "category_code": "citizen-services",
        "jurisdiction": "Karnataka",
        "jurisdiction_code": "IN-KA",
        "publisher": "Government of Karnataka — Seva Sindhu",
        "official_url": "https://sevasindhu.karnataka.gov.in/",
        "sources": [{"title": "Seva Sindhu official portal", "url": "https://sevasindhu.karnataka.gov.in/"}],
        "evidence": "The record points to the official Karnataka citizen-services portal; individual service conditions are not asserted here.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-pm-kisan",
        "title": "PM-KISAN",
        "code": "DEMO-PM-KISAN",
        "description": "The official PM-KISAN portal provides information and citizen-facing services for the PM-KISAN programme. Check the portal for current eligibility and status guidance.",
        "category": "Agriculture",
        "category_code": "agriculture",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Government of India — PM-KISAN",
        "official_url": "https://pmkisan.gov.in/",
        "sources": [{"title": "PM-KISAN official portal", "url": "https://pmkisan.gov.in/"}],
        "evidence": "The record links to the official PM-KISAN programme portal; no benefit amount or eligibility claim is made.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-ayushman-bharat",
        "title": "Ayushman Bharat PM-JAY",
        "code": "DEMO-PMJAY",
        "description": "The official PM-JAY portal provides information about Ayushman Bharat Pradhan Mantri Jan Arogya Yojana and its citizen services.",
        "category": "Healthcare",
        "category_code": "healthcare",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "National Health Authority — PM-JAY",
        "official_url": "https://pmjay.gov.in/",
        "sources": [{"title": "PM-JAY official portal", "url": "https://pmjay.gov.in/"}],
        "evidence": "The record links to the official PM-JAY portal; scheme-specific coverage and eligibility are not asserted here.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-national-career-service",
        "title": "National Career Service",
        "code": "DEMO-NCS",
        "description": "The official National Career Service portal provides employment and career-service information for job seekers and other users.",
        "category": "Employment",
        "category_code": "employment",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Ministry of Labour and Employment — National Career Service",
        "official_url": "https://www.ncs.gov.in/",
        "sources": [{"title": "National Career Service", "url": "https://www.ncs.gov.in/"}],
        "evidence": "The record links to the official National Career Service portal; individual job or eligibility outcomes are not asserted.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-nsap",
        "title": "National Social Assistance Programme",
        "code": "DEMO-NSAP",
        "description": "The official NSAP portal provides programme information for India's national social-assistance schemes. Current state-specific rules must be checked before applying.",
        "category": "Pensions and social welfare",
        "category_code": "social-welfare",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Ministry of Rural Development — NSAP",
        "official_url": "https://nsap.nic.in/",
        "sources": [{"title": "NSAP official portal", "url": "https://nsap.nic.in/"}],
        "evidence": "The record links to the official National Social Assistance Programme portal; pension eligibility and amounts are not asserted.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-udyam-registration",
        "title": "Udyam Registration",
        "code": "DEMO-UDYAM",
        "description": "The official Udyam Registration portal is the government entry point for checking current MSME registration guidance.",
        "category": "MSME and entrepreneurship",
        "category_code": "entrepreneurship",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Ministry of Micro, Small and Medium Enterprises — Udyam",
        "official_url": "https://udyamregistration.gov.in/",
        "sources": [{"title": "Udyam Registration official portal", "url": "https://udyamregistration.gov.in/"}],
        "evidence": "The record links to the official Udyam Registration portal; registration conditions are not asserted here.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
    {
        "id": "demo-stand-up-india",
        "title": "Stand-Up India",
        "code": "DEMO-STAND-UP-INDIA",
        "description": "The official Stand-Up India portal provides information about the programme and its application channel for eligible entrepreneurs; current conditions must be checked on the portal.",
        "category": "Women and entrepreneurship",
        "category_code": "women-entrepreneurs",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Stand-Up India",
        "official_url": "https://www.standupmitra.in/",
        "sources": [{"title": "Stand-Up India official portal", "url": "https://www.standupmitra.in/"}],
        "evidence": "The record links to the official Stand-Up India portal; detailed eligibility, finance, and document claims are not asserted.",
        "details": {"eligibility": [], "benefits": [], "documents": [], "steps": []},
    },
]


def demo_source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item["title"],
        "publisher": item["publisher"],
        "url": item["official_url"],
        "authority_status": "official source link; demonstration record not production-verified",
        "checked_on": DEMO_CHECKED_ON,
    }


def demo_items(question: str = "", *, category: str = "", jurisdiction: str = "") -> list[dict[str, Any]]:
    stop_words = {
        "what", "which", "where", "when", "how", "can", "could", "would", "should",
        "are", "is", "the", "for", "and", "with", "from", "about", "please", "tell",
        "me", "in", "on", "to", "a", "an", "my", "i", "do", "if", "any",
    }
    terms = {
        term.strip("?!.,:;").casefold()
        for term in question.split()
        if len(term.strip("?!.,:;")) > 2 and term.strip("?!.,:;").casefold() not in stop_words
    }
    keyword_groups = {
        "education": {"scholarship", "scholarships", "student", "students", "college", "education", "nsp"},
        "identity": {"aadhaar", "address", "biometric", "enrolment", "update"},
        "certificates": {"certificate", "caste", "income", "nadakacheri"},
        "citizen-services": {"seva", "sindhu", "citizen"},
        "agriculture": {"farmer", "farmers", "agriculture", "pm-kisan", "kisan"},
        "healthcare": {"health", "healthcare", "ayushman", "pm-jay"},
        "employment": {"employment", "job", "jobs", "career", "unemployed", "graduate"},
        "social-welfare": {"pension", "welfare", "assistance", "nsap"},
        "entrepreneurship": {"msme", "udyam", "entrepreneur", "entrepreneurs", "entrepreneurship"},
        "women-entrepreneurs": {"women", "woman", "entrepreneur", "entrepreneurs", "stand-up"},
    }
    matched_domains = {
        code for code, keywords in keyword_groups.items() if terms.intersection(keywords)
    }
    specific_terms = {"income", "caste", "scholarship", "scholarships", "aadhaar", "address", "pension", "ayushman", "udyam", "kisan", "farmer", "farmers", "women", "stand-up"}
    requested_specific = terms.intersection(specific_terms)
    result = []
    for item in DEMO_SERVICES:
        haystack = " ".join(
            [item["title"], item["description"], item["category"], item["jurisdiction"], item["publisher"]]
        ).casefold()
        if category and category.casefold() not in item["category_code"].casefold() and category.casefold() not in item["category"].casefold():
            continue
        if jurisdiction and jurisdiction.casefold() not in item["jurisdiction_code"].casefold() and jurisdiction.casefold() not in item["jurisdiction"].casefold():
            continue
        item_keywords = keyword_groups.get(item["category_code"], set())
        if matched_domains and item["category_code"] not in matched_domains and not item_keywords.intersection(terms):
            continue
        if requested_specific and not any(
            term in haystack
            or (term in {"farmer", "farmers", "women"} and item["category_code"] in matched_domains)
            for term in requested_specific
        ):
            continue
        score = sum(term in haystack or term in item_keywords for term in terms)
        if terms and score == 0:
            continue
        copy = dict(item)
        copy["demo"] = True
        copy["checked_on"] = DEMO_CHECKED_ON
        copy["score"] = score
        result.append(copy)
    result.sort(key=lambda value: (-value["score"], value["title"]))
    return result


def demo_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": f"demo:{item['id']}",
        "fact_type": "demonstration_source_summary",
        "text": item["evidence"],
        "publisher": item["publisher"],
        "source_url": item["official_url"],
        "source_snapshot_id": f"demo-checked-{item['checked_on']}",
        "evidence_locator": {"quoted_text": item["evidence"], "checked_on": item["checked_on"]},
        "language": "en",
        "service": {"service_name": item["title"], "service_version_id": item["id"]},
        "supporting_sources": [
            {
                "fact_id": f"demo:{item['id']}",
                "publisher": item["publisher"],
                "url": item["official_url"],
                "source_snapshot_id": f"demo-checked-{item['checked_on']}",
                "service_name": item["title"],
                "evidence_excerpt": item["evidence"],
            }
        ],
    }


def demo_answer(question: str, items: list[dict[str, Any]], history: list[str] | None = None) -> str:
    if not items:
        return (
            "I could not find a matching demonstration record. The production knowledge base still requires human verification and publication before it can answer from verified facts."
        )
    lines = [
        "Demonstration information (official links checked on 2026-11-06; this is not published production knowledge):",
        "",
        "Relevant services:",
    ]
    for item in items[:5]:
        lines.append(f"- {item['title']}: {item['description']} [S{items.index(item) + 1}]")
    lines.extend(
        [
            "",
            "The linked portal is the authoritative place to confirm current eligibility, documents, fees, deadlines, and application status. Those details are not asserted here unless shown above.",
            "",
            "If you tell me your state and the specific service, I can narrow this demonstration list.",
        ]
    )
    return "\n".join(lines)
