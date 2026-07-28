"""Persist batch Excel exports only after format verification."""
from __future__ import annotations

import os
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.export_service import verify_shortlisted_export


def download_excel_name(file_name: str) -> str:
    """Hide internal batch-id/collision suffixes in browser downloads."""
    name = str(file_name or "").strip()
    if not name:
        return ""
    return re.sub(
        r"_[0-9a-f]{8}(?:_\d+)?(?=\.xlsx$)",
        "",
        name,
        flags=re.IGNORECASE,
    )


def persist_verified_export(db: Session, batch_id: str, export_result: dict) -> dict:
    if not export_result or not export_result.get("file_path"):
        raise ValueError("Export result missing file_path")

    file_path = str(export_result["file_path"]).replace("\\", "/")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Export file not found: {file_path}")

    verify_shortlisted_export(file_path)

    existing = db.execute(
        text("""
        SELECT id FROM batch_exports
        WHERE batch_id = :batch_id
        ORDER BY id DESC
        LIMIT 1
    """),
        {"batch_id": batch_id},
    ).fetchone()

    if existing:
        db.execute(
            text("""
            UPDATE batch_exports
            SET excel_file=:excel_file, created_at=:created_at
            WHERE id=:id
        """),
            {
                "excel_file": file_path,
                "created_at": export_result["generated_at"],
                "id": existing[0],
            },
        )
    else:
        db.execute(
            text("""
            INSERT INTO batch_exports(batch_id, excel_file, created_at)
            VALUES(:batch_id, :excel_file, :created_at)
        """),
            {
                "batch_id": batch_id,
                "excel_file": file_path,
                "created_at": export_result["generated_at"],
            },
        )

    db.commit()

    return {
        "success": True,
        "excel_file": file_path,
        "excel_name": download_excel_name(
            export_result.get("file_name") or os.path.basename(file_path)
        ),
        "created_at": export_result["generated_at"].isoformat(),
        "generated_at_sl": export_result.get("generated_at_sl"),
    }
