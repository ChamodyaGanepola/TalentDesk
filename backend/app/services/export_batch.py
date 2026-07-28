"""Generate shortlisted Excel exports (in-process with subprocess fallback)."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def generate_batch_export(
    batch_id: str,
    *,
    db: Session | None = None,
    total_cvs: int | None = None,
    position: str | None = None,
) -> dict | None:
    from app.services.export_runner import export_batch_in_subprocess
    from app.services.export_service import export_batch_shortlisted

    lookup_db = db
    owned = False
    if lookup_db is None:
        from app.db_mysql import SessionLocal

        lookup_db = SessionLocal()
        owned = True

    try:
        if total_cvs is None:
            total_cvs = lookup_db.execute(
                text("SELECT COUNT(*) FROM uploads WHERE batch_id = :batch_id"),
                {"batch_id": batch_id},
            ).scalar() or 0

        batch_profession = " ".join(str(position or "").strip().split())
        if not batch_profession:
            batch_profession = str(
                lookup_db.execute(
                    text("""
                    SELECT profession FROM upload_batches
                    WHERE batch_id = :batch_id LIMIT 1
                """),
                    {"batch_id": batch_id},
                ).scalar()
                or ""
            ).strip()

        result = None
        try:
            result = export_batch_shortlisted(
                batch_id,
                total_cvs=int(total_cvs),
                db=lookup_db,
                position=batch_profession or None,
            )
        except Exception as exc:
            print("In-process Excel export failed:", exc)

        if not result:
            try:
                result = export_batch_in_subprocess(
                    batch_id,
                    total_cvs=int(total_cvs),
                    position=batch_profession or None,
                )
            except Exception as exc:
                print("Subprocess Excel export failed:", exc)

        return result
    finally:
        if owned:
            lookup_db.close()
