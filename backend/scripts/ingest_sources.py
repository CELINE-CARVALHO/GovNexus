
import json

from backend.database.connection import SessionLocal
from backend.services.source_ingestion import ingest_all_active_sources


def main():
    db = SessionLocal()

    try:
        results = ingest_all_active_sources(db)

        print(json.dumps(results, indent=2, default=str))

        print("\nIngestion summary:")
        print("Total:", len(results))
        print(
            "Successful:",
            sum(
                r["status"] in {"ingested", "unchanged"}
                for r in results
            ),
        )
        print(
            "Failed:",
            sum(r["status"] == "failed" for r in results),
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
