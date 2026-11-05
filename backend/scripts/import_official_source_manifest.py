from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models.language import Language
from backend.database.models.location import Location
from backend.database.models.source import Source
from backend.services.source_ingestion import (
    UnsafeSourceURL,
    canonical_url_hash,
    validate_public_url,
)

MAX_MANIFEST_BYTES = 1_000_000
MAX_SOURCE_RECORDS = 100
OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")
ALLOWED_SOURCE_TYPES = {"government_portal", "official_website"}


def load_manifest(path: Path) -> list[dict[str, Any]]:
    content = path.read_bytes()
    if len(content) > MAX_MANIFEST_BYTES:
        raise ValueError("Source manifest must be no larger than 1 MB.")

    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(content.decode("utf-8-sig").splitlines()))
    elif path.suffix.lower() == ".json":
        payload = json.loads(content)
        rows = payload.get("sources") if isinstance(payload, dict) else payload
    else:
        raise ValueError("Manifest must be a .json or .csv file.")

    if not isinstance(rows, list) or not rows:
        raise ValueError("Manifest must contain at least one source record.")
    if len(rows) > MAX_SOURCE_RECORDS:
        raise ValueError(f"Manifest may contain at most {MAX_SOURCE_RECORDS} records.")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Every manifest entry must be an object or CSV row.")
    return rows


def _official_hostname(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Source URL must be an HTTPS URL with a hostname.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-standard HTTPS ports are not allowed.")
    hostname = parsed.hostname.rstrip(".").lower()
    if not any(hostname.endswith(suffix) for suffix in OFFICIAL_SUFFIXES):
        raise ValueError("Only .gov.in and .nic.in source domains are accepted.")
    return hostname


def register_manifest_sources(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    url_validator: Callable[[str], str] = validate_public_url,
) -> dict[str, int]:
    created = 0
    existing = 0

    for row in rows:
        url = str(row.get("url") or "").strip()
        publisher = str(row.get("publisher_name") or "").strip()
        if not url or not publisher:
            raise ValueError("Each source requires url and publisher_name.")
        if len(url) > 2048 or len(publisher) > 255:
            raise ValueError("Source URL or publisher name exceeds its size limit.")

        _official_hostname(url)
        url_validator(url)
        url_hash = canonical_url_hash(url)
        if db.scalar(select(Source.id).where(Source.url_hash == url_hash)):
            existing += 1
            continue

        source_type = str(row.get("source_type") or "government_portal").strip()
        if source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"Unsupported source_type; use one of {sorted(ALLOWED_SOURCE_TYPES)}."
            )

        language_code = str(row.get("language_code") or "en").strip().lower()
        if db.get(Language, language_code) is None:
            raise ValueError(f"Language {language_code!r} is not in the master data.")

        jurisdiction_code = str(row.get("jurisdiction_code") or "").strip()
        jurisdiction_id = None
        if jurisdiction_code:
            location = db.scalar(
                select(Location).where(
                    Location.parent_id.is_(None),
                    Location.code == jurisdiction_code,
                )
            )
            if location is None:
                raise ValueError(
                    f"Unknown top-level jurisdiction code {jurisdiction_code!r}."
                )
            jurisdiction_id = location.id

        db.add(
            Source(
                url=url,
                url_hash=url_hash,
                publisher_name=publisher,
                source_type=source_type,
                authority_status="unverified",
                jurisdiction_location_id=jurisdiction_id,
                language_code=language_code,
                retrieval_interval_hours=24,
                is_active=False,
            )
        )
        created += 1

    db.flush()
    return {
        "created_unverified_inactive": created,
        "already_registered": existing,
        "received": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and register official-domain source URLs as inactive, "
            "unverified records. No pages are fetched."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist validated source records. Default behavior is dry-run.",
    )
    args = parser.parse_args()

    rows = load_manifest(args.manifest)
    db = SessionLocal()
    try:
        result = register_manifest_sources(db, rows)
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print("Source manifest validation complete.")
        print(f"Mode: {'apply' if args.apply else 'dry-run'}")
        for key, value in result.items():
            print(f"{key}: {value}")
        if args.apply:
            print("No sources were fetched, verified, or published.")
    except (ValueError, UnsafeSourceURL):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
