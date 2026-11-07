"""Read-only local demonstration knowledge.

This module is deliberately separate from SourceFact, verification, and
publication data.  Every item carries its official URL and the date checked.
It is suitable for a local demonstration only; it is not a publication path.
"""

from __future__ import annotations

from datetime import date
from typing import Any


DEMO_CHECKED_ON = date(2026, 11, 6).isoformat()
PM_KISAN_CHECKED_ON = date(2026, 11, 7).isoformat()
MYSCHEME_CHECKED_ON = date(2026, 11, 7).isoformat()
VERIFICATION_LABEL = "AI-researched information — pending human verification."


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
        "checked_on": PM_KISAN_CHECKED_ON,
        "verification_label": VERIFICATION_LABEL,
        "description": (
            "The official PM-KISAN homepage, retrieved on 2026-11-07, describes PM-KISAN as a "
            "Central Sector scheme with 100% funding from the Government of India, operational "
            "from 1.12.2018. It states that an income support of 6,000/- per year in three equal "
            "instalments will be provided to all landholding farmer families, and that the fund "
            "will be directly transferred to the bank accounts of the beneficiaries. It defines "
            "a family as husband, wife and minor children. It also states that eKYC is mandatory "
            "for PM-KISAN registered farmers."
        ),
        "category": "Agriculture",
        "category_code": "agriculture",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "Department of Agriculture and Farmers Welfare — PM-KISAN",
        "official_url": "https://pmkisan.gov.in/",
        "sources": [{"title": "PM-KISAN official portal", "url": "https://pmkisan.gov.in/"}],
        "evidence": (
            "Retrieved from https://pmkisan.gov.in/ on 2026-11-07. The page says PM Kisan is a "
            "Central Sector scheme with 100% funding from the Government of India, operational "
            "from 1.12.2018, and that an income support of 6,000/- per year in three equal "
            "instalments will be provided to all land holding farmer families. Family is defined "
            "as husband, wife and minor children. State Governments and UT administrations identify "
            "eligible families as per scheme guidelines. The page says all institutional land holders "
            "shall not be eligible, and lists further higher-economic-status exclusion categories. "
            "The page also states that eKYC is mandatory for PMKISAN registered farmers. "
            + VERIFICATION_LABEL
        ),
        "details": {
            "eligibility": [
                {
                    "description": "The official page says income support will be provided to all land holding farmer families. It defines a family for the scheme as husband, wife and minor children.",
                    "is_mandatory": True,
                    "prompt": "Are you part of a landholding farmer family, using the page's definition of family as husband, wife and minor children?",
                    "why": "The retrieved PM-KISAN page states that support is for all landholding farmer families and defines family as husband, wife and minor children.",
                    "input": "yes_no",
                    "expected": "yes",
                    "source_url": "https://pmkisan.gov.in/",
                    "retrieved_on": PM_KISAN_CHECKED_ON,
                },
                {
                    "description": "The official page says: All Institutional Land holders shall not be eligible for benefit under the scheme.",
                    "is_mandatory": True,
                    "prompt": "Is the land held by an institution rather than a farmer family?",
                    "why": "The retrieved page lists all institutional land holders as not eligible.",
                    "input": "yes_no",
                    "expected": "no",
                    "source_url": "https://pmkisan.gov.in/",
                    "retrieved_on": PM_KISAN_CHECKED_ON,
                },
                {
                    "description": (
                        "The official page says categories of beneficiaries of higher economic status shall not be eligible. "
                        "The listed categories are: former and present holders of constitutional posts; former and present Ministers, State Ministers, members of Parliament or State legislatures, Mayors of Municipal Corporations, and Chairpersons of District Panchayats; "
                        "all serving or retired officers and employees of Central or State Government Ministries, offices, departments and field units, Central or State PSEs and attached offices or autonomous institutions, and regular employees of local bodies, excluding Multi Tasking Staff / Class IV / Group D employees; "
                        "all superannuated or retired pensioners whose monthly pension is Rs.10,000/- or more, excluding Multi Tasking Staff / Class IV / Group D employees, of the above category; "
                        "all persons who paid Income Tax in the last assessment year; "
                        "and professionals such as Doctors, Engineers, Lawyers, Chartered Accountants, and Architects registered with professional bodies and carrying out the profession by undertaking practices."
                    ),
                    "is_mandatory": True,
                    "prompt": "Does the farmer family fall into one of the higher-economic-status exclusion categories printed on the official PM-KISAN page?",
                    "why": "The retrieved page says those higher-economic-status categories shall not be eligible. This question asks you to compare your situation with that published list. It is not a government decision.",
                    "input": "yes_no",
                    "expected": "no",
                    "source_url": "https://pmkisan.gov.in/",
                    "retrieved_on": PM_KISAN_CHECKED_ON,
                },
            ],
            "benefits": [
                {
                    "description": "The official page states an income support of 6,000/- per year in three equal instalments, transferred directly to the bank accounts of the beneficiaries.",
                    "source_url": "https://pmkisan.gov.in/",
                    "retrieved_on": PM_KISAN_CHECKED_ON,
                }
            ],
            "documents": [],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Use the official PM-KISAN portal",
                    "instructions": "The retrieved homepage lists New Farmer Registration and Know Your Status in the farmer corner. Confirm the current route on the official portal. This record does not reproduce an application form.",
                    "official_url": "https://pmkisan.gov.in/",
                }
            ],
        },
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
    {
        "id": "demo-myscheme",
        "title": "myScheme",
        "code": "DEMO-MYSCHEME",
        "checked_on": MYSCHEME_CHECKED_ON,
        "verification_label": VERIFICATION_LABEL,
        "description": (
            "myScheme's official homepage, retrieved on 2026-11-07, says myScheme is a national "
            "platform that aims to offer one-stop search and discovery of government schemes. "
            "It says the platform helps citizens find government schemes and guides them on how "
            "to apply, so they do not need to visit multiple government websites."
        ),
        "category": "Scheme discovery",
        "category_code": "discovery",
        "jurisdiction": "Central Government",
        "jurisdiction_code": "IN",
        "publisher": "myScheme, National e-Governance Division",
        "official_url": "https://www.myscheme.gov.in/",
        "sources": [
            {"title": "myScheme", "url": "https://www.myscheme.gov.in/"},
        ],
        "evidence": (
            "Retrieved from https://www.myscheme.gov.in/ on 2026-11-07. The page says myScheme "
            "is a national platform for search and discovery of government schemes from the Central "
            "Government and State and UT Governments, and that a user can enter basic details and "
            "then open a scheme page for eligibility, benefits, documents, application process, and "
            "the application URL. Contact shown on the page: 4th Floor, NeGD, Electronics Niketan, "
            "6 CGO Complex, Lodhi Road, New Delhi - 110003; phone (011) 24303714 (9:00 AM to 5:30 PM). "
            + VERIFICATION_LABEL
        ),
        "details": {
            "eligibility": [],
            "benefits": [
                {
                    "description": "The official page describes myScheme as a discovery platform. It does not state a cash benefit. It says citizens can discover schemes in one place instead of visiting multiple departmental websites.",
                    "source_url": "https://www.myscheme.gov.in/",
                    "retrieved_on": MYSCHEME_CHECKED_ON,
                }
            ],
            "documents": [],
            "steps": [
                {
                    "step_number": 1,
                    "title": "Enter basic details on myScheme",
                    "instructions": "The retrieved page says the user enters basic details such as demographic information, income, and social category.",
                    "official_url": "https://www.myscheme.gov.in/",
                },
                {
                    "step_number": 2,
                    "title": "Review the schemes the platform lists",
                    "instructions": "The retrieved page says myScheme then displays relevant schemes from the information provided. GovNexus does not repeat that matching result.",
                    "official_url": "https://www.myscheme.gov.in/",
                },
                {
                    "step_number": 3,
                    "title": "Open the scheme page and its application link",
                    "instructions": "The retrieved page says the user can open a scheme page for detailed knowledge, FAQs, and the application process, and can navigate to the respective application URL.",
                    "official_url": "https://www.myscheme.gov.in/",
                },
            ],
        },
    },
]


def demo_source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item["title"],
        "publisher": item["publisher"],
        "url": item["official_url"],
        "authority_status": "official source link; not production-verified",
        "checked_on": item.get("checked_on") or DEMO_CHECKED_ON,
        "verification_label": item.get("verification_label") or VERIFICATION_LABEL,
    }


def _matches_jurisdiction(item: dict[str, Any], jurisdiction: str) -> bool:
    if not jurisdiction:
        return True
    wanted = jurisdiction.casefold().strip()
    code = item["jurisdiction_code"].casefold()
    name = item["jurisdiction"].casefold()
    if wanted in {code, name}:
        return True
    # A state or UT selection still shows Central schemes.
    return code == "in" and wanted not in {"in", "central", "central government"}


def demo_items(
    question: str = "",
    *,
    category: str = "",
    jurisdiction: str = "",
    level: str = "",
) -> list[dict[str, Any]]:
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
        "discovery": {"myscheme", "my-scheme", "discover", "discovery"},
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
        if not _matches_jurisdiction(item, jurisdiction):
            continue
        if level == "central" and item["jurisdiction_code"] != "IN":
            continue
        if level == "state" and item["jurisdiction_code"] == "IN":
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
        copy["checked_on"] = item.get("checked_on") or DEMO_CHECKED_ON
        copy["verification_label"] = item.get("verification_label") or VERIFICATION_LABEL
        copy["score"] = score
        result.append(copy)
    result.sort(key=lambda value: (-value["score"], value["title"]))
    return result


def demo_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": f"demo:{item['id']}",
        "fact_type": "source_summary",
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


def demo_answer(
    question: str,
    items: list[dict[str, Any]],
    history: list[str] | None = None,
    language_code: str = "en",
) -> str:
    from backend.services.conversation_language import citizen_text, language_base

    if not items:
        return citizen_text("insufficient", language_code)
    if language_base(language_code) != "en":
        preface = citizen_text("source_original", language_code)
    focus = items[0]
    asked = f"{question} {' '.join(history or [])}".casefold()
    lines = [
        f"{VERIFICATION_LABEL} [S1]",
        "",
        f"## {focus['title']}",
        f"{focus['description']} [S1]",
    ]
    if language_base(language_code) != "en":
        lines.insert(0, preface)
        lines.insert(1, "")
    details = focus.get("details") or {}
    if any(word in asked for word in ("document", "documents", "paper")):
        documents = details.get("documents") or []
        lines.append("")
        lines.append("## Documents named in the stored record")
        if documents:
            for document in documents[:6]:
                name = document.get("name") or "Document"
                lines.append(f"{name} is listed in the stored record. [S1]")
        else:
            lines.append("A document list could not be confirmed from this record. [S1]")
    elif any(word in asked for word in ("eligib", "qualify", "who can")):
        rules = details.get("eligibility") or []
        lines.append("")
        lines.append("## Documented eligibility")
        if rules:
            for rule in rules[:6]:
                text = rule.get("description") or rule.get("prompt")
                if text:
                    lines.append(f"{text} [S1]")
        else:
            lines.append("A checkable eligibility rule could not be confirmed from this record. [S1]")
    lines.extend(
        [
            "",
            "Confirm current eligibility, documents, and application steps on the official page before you apply. [S1]",
            "This is not an approval and it is not a human-verified publication. [S1]",
        ]
    )
    return "\n".join(lines)
