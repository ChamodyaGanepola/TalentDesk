"""Keyset (cursor) pagination helpers."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def clamp_page_size(per_page: int | None) -> int:
    if per_page is None:
        return DEFAULT_PAGE_SIZE
    try:
        value = int(per_page)
    except Exception:
        return DEFAULT_PAGE_SIZE
    return min(max(value, 1), MAX_PAGE_SIZE)


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), default=str)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def parse_cursor_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1]
        return datetime.fromisoformat(text)
    except Exception:
        return None


def split_keyset_page(rows: list, per_page: int) -> tuple[list, bool]:
    """Return (items, has_more) using per_page+1 fetch pattern."""
    if len(rows) > per_page:
        return rows[:per_page], True
    return rows, False


def ensure_pagination_indexes(db) -> None:
    """Create indexes used by keyset pagination (idempotent)."""
    from sqlalchemy import text

    indexes = [
        ("uploads", "idx_uploads_created_id", "created_at DESC, id DESC"),
        ("uploads", "idx_uploads_batch_created_id", "batch_id, created_at DESC, id DESC"),
        ("batch_exports", "idx_batch_exports_id", "id DESC"),
        ("batch_exports", "idx_batch_exports_batch_id", "batch_id, id DESC"),
    ]

    for table, index_name, columns in indexes:
        try:
            exists = db.execute(text("""
                SELECT COUNT(*) AS c
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
                  AND index_name = :index_name
            """), {
                "table_name": table,
                "index_name": index_name,
            }).scalar()

            if not exists:
                db.execute(text(
                    f"CREATE INDEX {index_name} ON {table} ({columns})"
                ))
                db.commit()
                print(f"Created index {index_name} on {table}")
        except Exception as exc:
            print(f"Index {index_name} skipped:", exc)
            try:
                db.rollback()
            except Exception:
                pass
