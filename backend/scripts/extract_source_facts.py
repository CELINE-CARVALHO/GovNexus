from __future__ import annotations

import argparse

from backend.database.connection import SessionLocal
from backend.services.fact_extraction import extract_selected_snapshot_facts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract pending facts from explicitly selected source snapshots."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--snapshot-id", action="append", dest="snapshot_ids",
        help="Snapshot UUID to process; may be supplied more than once.",
    )
    selection.add_argument(
        "--source-id", action="append", dest="source_ids",
        help="Source UUID whose completed snapshots should be processed; may be repeated.",
    )
    selection.add_argument(
        "--all", action="store_true", dest="all_snapshots",
        help="Explicitly process every completed successful snapshot.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        results = extract_selected_snapshot_facts(
            db,
            snapshot_ids=args.snapshot_ids,
            source_ids=args.source_ids,
            all_snapshots=args.all_snapshots,
        )
        total_created = sum(item.get("created", 0) for item in results)
        total_existing = sum(item.get("existing", 0) for item in results)
        print("\n========== FACT EXTRACTION RESULTS ==========\n")
        for result in results:
            print(f"Snapshot: {result['snapshot_id']}")
            print(f"Status:   {result['status']}")
            if result.get("error"):
                print(f"Error:    {result['error']}")
            if result.get("reason"):
                print(f"Reason:   {result['reason']}")
            print(f"Created:  {result.get('created', 0)}")
            print(f"Existing: {result.get('existing', 0)}")
            print("---------------------------------------------")
        print("\n============== FINAL SUMMARY ==============")
        print(f"Snapshots processed: {len(results)}")
        print(f"New facts created:   {total_created}")
        print(f"Existing facts:      {total_existing}")
        print("============================================\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
