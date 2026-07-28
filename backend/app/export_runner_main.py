"""
Fresh-process Excel export (always loads current export_service from disk).
Invoked via: python -m app.export_runner_main <batch_id> [--total-cvs N] [--position TITLE]
"""
from __future__ import annotations

import argparse
import json
import sys

from app.db_mysql import SessionLocal
from app.services.export_service import export_batch_shortlisted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_id")
    parser.add_argument("--total-cvs", type=int, default=None)
    parser.add_argument("--position", default="")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        position = " ".join(str(args.position or "").strip().split()) or None
        result = export_batch_shortlisted(
            args.batch_id,
            total_cvs=args.total_cvs,
            db=db,
            position=position,
        )
    finally:
        db.close()

    if not result:
        print("null")
        return 1

    payload = {
        "file_path": result["file_path"],
        "file_name": result["file_name"],
        "generated_at": result["generated_at"].isoformat(),
        "generated_at_sl": result.get("generated_at_sl"),
        "batch_no": result.get("batch_no"),
        "cv_count": result.get("cv_count"),
        "shortlisted_count": result.get("shortlisted_count"),
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
