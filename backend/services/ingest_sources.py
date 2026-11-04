
import json

from backend.database.connection import SessionLocal
from backend.services.source_ingestion import ingest_all_active_sources


def main():
    db = SessionLocal()

    try:
        results = ingest_all_active_sources(db)

        print("\n========== SOURCE INGESTION ==========")

        for result in results:
            print(json.dumps(result, indent=2, default=str))

        print("\n========== SUMMARY ==========")
        print(f"Sources processed: {len(results)}")
        print(
            "New snapshots:",
            sum(r["status"] == "new_snapshot" for r in results),
        )
        print(
            "Unchanged:",
            sum(r["status"] == "unchanged" for r in results),
        )
        print(
            "Failed:",
            sum(r["status"] == "failed" for r in results),
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
