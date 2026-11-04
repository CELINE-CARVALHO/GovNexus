
from __future__ import annotations

import hashlib
from datetime import date
from sqlalchemy import Enum as SAEnum

from backend.database.connection import SessionLocal
from backend.database.models.category import Category
from backend.database.models.department import Department
from backend.database.models.service import Service
from backend.database.models.service_version import (
    ServiceVersion,
    ServiceTranslation,
)
from backend.database.models.source import Source


SERVICES = [
    {
        "code": "AADHAAR-UPDATE",
        "slug": "aadhaar-update",
        "category": "identity",
        "department_code": "uidai",
        "department_level": "central",
        "department_url": "https://uidai.gov.in/en/",
        "department_name": "Unique Identification Authority of India",
        "title": "Aadhaar Update Services",
        "description": (
            "Official Aadhaar services and information for residents, "
            "including available update facilities."
        ),
        "application_url": "https://myaadhaar.uidai.gov.in/",
        "source_url": "https://uidai.gov.in/en",
        "publisher": "Unique Identification Authority of India",
    },
    {
        "code": "PAN-SERVICES",
        "slug": "pan-services",
        "category": "identity",
        "department_code": "income-tax",
        "department_level": "central",
        "department_url": "https://www.incometax.gov.in/",
        "department_name": "Income Tax Department",
        "title": "PAN Application and Correction Services",
        "description": (
            "Official information about PAN applications, changes "
            "and corrections."
        ),
        "application_url": (
            "https://www.incometaxindia.gov.in/en/tax-services/apply-for-pan"
        ),
        "source_url": (
            "https://www.incometaxindia.gov.in/en/tax-services/apply-for-pan"
        ),
        "publisher": "Income Tax Department, Government of India",
    },
    {
        "code": "NATIONAL-SCHOLARSHIP-PORTAL",
        "slug": "national-scholarship-portal",
        "category": "education",
        "department_code": "national-scholarship-portal",
        "department_level": "central",
        "department_url": "https://scholarships.gov.in/",
        "department_name": "National Scholarship Portal",
        "title": "National Scholarship Portal",
        "description": (
            "Government portal providing access to scholarship "
            "information and student application services."
        ),
        "application_url": "https://scholarships.gov.in/Students",
        "source_url": "https://scholarships.gov.in/Students",
        "publisher": "National Scholarship Portal, Government of India",
    },
]


def enum_value(column, preferred):
    """Return a valid enum value without guessing unsupported values."""
    column_type = column.type

    if isinstance(column_type, SAEnum):
        choices = list(column_type.enums)
        for candidate in preferred:
            if candidate in choices:
                return candidate
        raise RuntimeError(
            f"No supported value found for {column.name}. "
            f"Available values: {choices}"
        )

    return preferred[0]


def get_or_create_department(db, item):
    department = (
        db.query(Department)
        .filter(Department.code == item["department_code"])
        .first()
    )

    if department:
        return department

    level = enum_value(
        Department.__table__.columns.level,
        ["central", "national", "ministry", "department"],
    )

    department = Department(
        code=item["department_code"],
        level=level,
        website_url=item["department_url"],
        is_active=True,
    )

    db.add(department)
    db.flush()
    return department


def get_or_create_source(db, item):
    url = item["source_url"].strip()
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

    source = (
        db.query(Source)
        .filter(Source.url_hash == url_hash)
        .first()
    )

    if source:
        return source

    source_type = enum_value(
        Source.__table__.columns.source_type,
        ["government_portal", "official_website", "website"],
    )

    authority_status = enum_value(
        Source.__table__.columns.authority_status,
        ["official", "authoritative", "unverified"],
    )

    source = Source(
        url=url,
        url_hash=url_hash,
        publisher_name=item["publisher"],
        source_type=source_type,
        authority_status=authority_status,
        language_code="en",
        retrieval_interval_hours=24,
        is_active=True,
    )

    db.add(source)
    db.flush()
    return source


def seed():
    db = SessionLocal()

    created_services = 0
    existing_services = 0
    created_sources = 0

    try:
        identity_category = (
            db.query(Category)
            .filter(Category.code == "identity")
            .first()
        )

        education_category = (
            db.query(Category)
            .filter(Category.code == "education")
            .first()
        )

        if not identity_category or not education_category:
            raise RuntimeError(
                "Required categories not found. "
                "Run seed_reference_data.py first."
            )

        categories = {
            "identity": identity_category,
            "education": education_category,
        }

        for item in SERVICES:
            existing = (
                db.query(Service)
                .filter(Service.code == item["code"])
                .first()
            )

            if existing:
                existing_services += 1
                get_or_create_source(db, item)
                continue

            department = get_or_create_department(db, item)
            category = categories[item["category"]]

            service_status = enum_value(
                Service.__table__.columns.status,
                ["draft", "pending_review", "inactive"],
            )

            service = Service(
                code=item["code"],
                slug=item["slug"],
                department_id=department.id,
                category_id=category.id,
                status=service_status,
                is_active=False,
            )

            db.add(service)
            db.flush()

            publication_status = enum_value(
                ServiceVersion.__table__.columns.publication_status,
                ["draft", "pending_review"],
            )

            version = ServiceVersion(
                service_id=service.id,
                version_number=1,
                effective_from=date.today(),
                publication_status=publication_status,
                change_summary="Initial catalogue entry; awaiting evidence review.",
            )

            db.add(version)
            db.flush()

            translation = ServiceTranslation(
                service_version_id=version.id,
                language_code="en",
                title=item["title"],
                description=item["description"],
                application_url=item["application_url"],
            )

            db.add(translation)

            source_before = (
                db.query(Source)
                .filter(
                    Source.url_hash
                    == hashlib.sha256(
                        item["source_url"].strip().encode("utf-8")
                    ).hexdigest()
                )
                .first()
            )

            get_or_create_source(db, item)

            if not source_before:
                created_sources += 1

            created_services += 1

        db.commit()

        print("\nSchemeSathi catalogue seed completed.")
        print(f"New services: {created_services}")
        print(f"Existing services: {existing_services}")
        print(f"New official source records: {created_sources}")
        print("\nAll newly created services remain unpublished.")
        print("No source snapshots or verified facts were fabricated.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()
