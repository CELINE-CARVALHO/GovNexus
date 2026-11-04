
import json

from backend.database.connection import SessionLocal
from backend.services.fact_extraction import (
    extract_all_snapshot_facts,
)


def main():
    db = SessionLocal()

    try:
        results = extract_all_snapshot_facts(db)

        print(
            json.dumps(
                results,
                indent=2,
                ensure_ascii=False,
            )
        )

        print("\n========== SUMMARY ==========")

        print(
            "Snapshots processed:",
            len(results),
        )

        print(
            "Facts created:",
            sum(item.get("created", 0) for item in results),
        )

        print(
            "Existing facts:",
            sum(item.get("existing", 0) for item in results),
        )

        print(
            "Failed snapshots:",
            sum(
                1
                for item in results
                if item.get("status") == "failed"
            ),
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
