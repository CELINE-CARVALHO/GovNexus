from __future__ import annotations

from backend.database.connection import SessionLocal
from backend.services.fact_extraction import extract_all_snapshot_facts


def main() -> None:
    db = SessionLocal()

    try:
        results = extract_all_snapshot_facts(db)

        total_created = 0
        total_existing = 0

        print("\n========== FACT EXTRACTION RESULTS ==========\n")

        for result in results:
            print(f"Snapshot: {result['snapshot_id']}")
            print(f"Status:   {result['status']}")

            if result["status"] == "failed":
                print(f"Error:    {result.get('error')}")

            if result.get("reason"):
                print(f"Reason:   {result['reason']}")

            print(f"Created:  {result.get('created', 0)}")
            print(f"Existing: {result.get('existing', 0)}")
            print("---------------------------------------------")

            total_created += result.get("created", 0)
            total_existing += result.get("existing", 0)

        print("\n============== FINAL SUMMARY ==============")
        print(f"Snapshots processed: {len(results)}")
        print(f"New facts created:   {total_created}")
        print(f"Existing facts:      {total_existing}")
        print("============================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
