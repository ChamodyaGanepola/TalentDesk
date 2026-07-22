from openpyxl import Workbook
from openpyxl.styles import Font
from app.db_mongo import cv_collection
from app.services.utils_experience import years_to_months
from app.services.timezone_sl import now_sri_lanka, now_utc_naive, to_sri_lanka
from datetime import datetime
from sqlalchemy import text
import os
import re

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


def safe_join(values):
    if not values:
        return ""

    return ", ".join([str(v) for v in values if v])


def get_batch_number_for_day(db, batch_id: str, batch_created_at: datetime | None) -> int:
    """Batch-1 = first batch on that Sri Lankan calendar day."""
    if not db or not batch_id:
        return 1

    try:
        rows = db.execute(text("""
            SELECT batch_id, created_at
            FROM upload_batches
            WHERE created_at IS NOT NULL
            ORDER BY created_at ASC
        """)).mappings().all()

        target = None
        for row in rows:
            if row["batch_id"] == batch_id:
                target = row["created_at"]
                break

        if target is None:
            target = batch_created_at

        if target is None:
            return 1

        target_sl = to_sri_lanka(target if isinstance(target, datetime) else batch_created_at)
        target_day = target_sl.date()

        same_day = []
        for row in rows:
            created = row["created_at"]
            if not created:
                continue
            created_sl = to_sri_lanka(created)
            if created_sl.date() == target_day:
                same_day.append(row["batch_id"])

        if batch_id in same_day:
            return same_day.index(batch_id) + 1

        return len(same_day) + 1
    except Exception as e:
        print("Batch number lookup error:", e)
        return 1


def build_excel_filename(
    cv_count: int,
    batch_no: int = 1,
    when: datetime | None = None,
) -> str:
    """e.g. 2026-07-22-113045-Batch-1-1CVs.xlsx (Sri Lanka time)"""
    stamp = to_sri_lanka(when) if when else now_sri_lanka()
    date_part = stamp.strftime("%Y-%m-%d")
    time_part = stamp.strftime("%H%M%S")
    count = max(int(cv_count or 0), 0)
    batch_label = f"Batch-{max(int(batch_no or 1), 1)}"
    return f"{date_part}-{time_part}-{batch_label}-{count}CVs.xlsx"


def candidate_experience_months(candidate: dict) -> int:
    if candidate.get("experience_months") is not None:
        try:
            return max(int(candidate.get("experience_months") or 0), 0)
        except Exception:
            pass

    return years_to_months(candidate.get("experience_years", 0))


def _is_shortlisted(status) -> bool:
    return str(status or "").strip().lower() == "shortlisted"


def _find_mongo_candidate(upload_id, batch_id: str, file_name: str | None = None):
    """Resolve CV data from Mongo for a shortlisted MySQL upload."""
    queries = [
        {"upload_id": upload_id},
        {"upload_id": str(upload_id)},
    ]

    try:
        queries.append({"upload_id": int(upload_id)})
    except Exception:
        pass

    for query in queries:
        doc = cv_collection.find_one(query)
        if doc:
            return doc

    if file_name:
        doc = cv_collection.find_one({
            "batch_id": batch_id,
            "file_name": file_name,
        })
        if doc:
            return doc

    return None


def load_shortlisted_candidates(batch_id: str, db=None) -> list[dict]:
    """
    Include every shortlisted CV in the batch.
    MySQL Shortlisted rows are the source of truth; Mongo supplies parsed fields.
    """
    candidates: list[dict] = []
    seen_upload_ids: set = set()

    if db is not None:
        try:
            rows = db.execute(text("""
                SELECT id, file_name, file_url
                FROM uploads
                WHERE batch_id = :batch_id
                  AND status = 'Shortlisted'
                ORDER BY id ASC
            """), {
                "batch_id": batch_id
            }).mappings().all()
        except Exception as e:
            print("Shortlisted MySQL lookup error:", e)
            rows = []

        for row in rows:
            upload_id = row["id"]
            file_name = row.get("file_name") or ""
            doc = _find_mongo_candidate(upload_id, batch_id, file_name)

            if doc:
                # Keep a plain dict and force shortlisted status for export.
                candidate = dict(doc)
                candidate["status"] = "Shortlisted"
                if not candidate.get("file_name"):
                    candidate["file_name"] = file_name
                candidates.append(candidate)
            else:
                # Still include the CV so Excel is generated for any shortlist.
                candidates.append({
                    "upload_id": upload_id,
                    "batch_id": batch_id,
                    "name": "",
                    "email": "",
                    "contact_no": "",
                    "skills": [],
                    "qualifications": [],
                    "experience_months": 0,
                    "file_name": file_name,
                    "status": "Shortlisted",
                })

            seen_upload_ids.add(upload_id)
            seen_upload_ids.add(str(upload_id))

        if candidates:
            print(
                f"Export: {len(candidates)} shortlisted CV(s) "
                f"from MySQL for batch {batch_id}"
            )
            return candidates

    # Fallback: Mongo only (case-insensitive status).
    try:
        for doc in cv_collection.find({"batch_id": batch_id}):
            if not _is_shortlisted(doc.get("status")):
                continue

            upload_id = doc.get("upload_id")
            if upload_id in seen_upload_ids or str(upload_id) in seen_upload_ids:
                continue

            candidate = dict(doc)
            candidate["status"] = "Shortlisted"
            candidates.append(candidate)
    except Exception as e:
        print("Shortlisted Mongo lookup error:", e)

    print(
        f"Export: {len(candidates)} shortlisted CV(s) "
        f"from Mongo for batch {batch_id}"
    )
    return candidates


def export_batch_shortlisted(
    batch_id: str,
    total_cvs: int | None = None,
    batch_no: int | None = None,
    when: datetime | None = None,
    db=None,
):
    candidates = load_shortlisted_candidates(batch_id, db=db)

    if not candidates:
        print(f"Export skipped: no shortlisted candidates for batch {batch_id}")
        return None

    stamp = to_sri_lanka(when) if when else now_sri_lanka()

    if batch_no is None:
        batch_no = get_batch_number_for_day(db, batch_id, when)

    wb = Workbook()
    ws = wb.active
    ws.title = "Shortlisted"

    headers = [
        "No",
        "Name",
        "CV File",
        "Email Address",
        "Contact No",
        "Skills",
        "Total Work Experience (months)",
        "Professional Qualifications"
    ]

    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for index, candidate in enumerate(candidates, start=1):
        months = candidate_experience_months(candidate)

        ws.append([
            index,
            candidate.get("name", "") or "",
            candidate.get("file_name", "") or "",
            candidate.get("email", "") or "",
            candidate.get("contact_no", "") or "",
            safe_join(candidate.get("skills", [])),
            months,
            safe_join(candidate.get("qualifications", []))
        ])

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            value = str(cell.value or "")
            max_length = max(max_length, len(value))

        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    # Filename uses total CVs in the batch; sheet rows = shortlisted only.
    cv_count = total_cvs if total_cvs is not None else len(candidates)
    file_name = build_excel_filename(cv_count, batch_no=batch_no, when=stamp)
    file_name = re.sub(r"[^\w.\-]+", "_", file_name)
    file_path = os.path.join(EXPORT_DIR, file_name)

    if os.path.exists(file_path):
        base, ext = os.path.splitext(file_name)
        file_name = f"{base}_{batch_id[:8]}{ext}"
        file_path = os.path.join(EXPORT_DIR, file_name)

    wb.save(file_path)

    print(
        f"Excel generated: {file_name} "
        f"({len(candidates)} shortlisted row(s), batch total {cv_count} CV(s))"
    )

    return {
        "file_path": file_path.replace("\\", "/"),
        "file_name": file_name,
        "generated_at": now_utc_naive(),
        "generated_at_sl": stamp.strftime("%Y-%m-%d %H:%M:%S"),
        "batch_no": batch_no,
        "cv_count": cv_count,
        "shortlisted_count": len(candidates),
    }
