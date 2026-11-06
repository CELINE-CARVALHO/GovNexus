from __future__ import annotations

import argparse
import json
from uuid import UUID

from sqlalchemy import select

from backend.database.connection import SessionLocal
from backend.database.models.source import Source
from backend.services.source_ingestion import ingest_source


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch only explicitly selected, active, human-reviewed sources."
    )
    parser.add_argument(
        "--source-id",
        action="append",
        required=True,
        help="Source UUID to ingest; repeat for each source.",
    )
    parser.add_argument(
        "--confirm-network-fetch",
        action="store_true",
        help="Required acknowledgement that selected public URLs will be fetched.",
    )
    args = parser.parse_args()
    if not args.confirm_network_fetch:
        parser.error("Pass --confirm-network-fetch to perform network requests.")

    try:
        source_ids = list(dict.fromkeys(UUID(value) for value in args.source_id))
    except ValueError as exc:
        parser.error(f"Invalid source UUID: {exc}")
    if len(source_ids) > 50:
        parser.error("At most 50 source IDs may be ingested in one run.")

    db = SessionLocal()
    try:
        sources = db.scalars(
            select(Source).where(Source.id.in_(source_ids))
        ).all()
        by_id = {source.id: source for source in sources}
        missing = [str(source_id) for source_id in source_ids if source_id not in by_id]
        if missing:
            raise ValueError(f"Unknown source IDs: {', '.join(missing)}")

        results = []
        for source_id in source_ids:
            source = by_id[source_id]
            if not source.is_active or (source.authority_status or "").lower() not in {
                "official",
                "authoritative",
                "verified",
            }:
                raise ValueError(
                    f"Source {source_id} must be active and manually authority-verified."
                )
            results.append(ingest_source(db, source))
        print(json.dumps(results, indent=2, default=str))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
