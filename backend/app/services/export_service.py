from openpyxl import Workbook
from openpyxl.styles import Font
from app.db_mongo import cv_collection
from app.services.utils_experience import resolve_experience_months
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


def slug_position(position: str) -> str:
    """Safe filename fragment from hiring position, e.g. Software Engineer → Software-Engineer."""
    text = " ".join(str(position or "").strip().split())
    if not text:
        return ""
    text = re.sub(r"[^\w\s\-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"[-\s]+", "-", text).strip("-_")
    return text[:60]


def build_excel_filename(
    cv_count: int,
    batch_no: int = 1,
    when: datetime | None = None,
    position: str = "",
) -> str:
    """e.g. 2026-07-22-113045-Batch-1-Software-Engineer-1CVs.xlsx"""
    stamp = to_sri_lanka(when) if when else now_sri_lanka()
    date_part = stamp.strftime("%Y-%m-%d")
    time_part = stamp.strftime("%H%M%S")
    count = max(int(cv_count or 0), 0)
    batch_label = f"Batch-{max(int(batch_no or 1), 1)}"
    position_slug = slug_position(position)
    if position_slug:
        return f"{date_part}-{time_part}-{batch_label}-{position_slug}-{count}CVs.xlsx"
    return f"{date_part}-{time_part}-{batch_label}-{count}CVs.xlsx"


def sanitize_excel_filename(file_name: str, position: str = "") -> str:
    """
    Keep a safe Windows filename while preserving the position slug.
    """
    position_slug = slug_position(position)
    # Allow letters, digits, dot, hyphen, underscore only.
    cleaned = re.sub(r"[^\w.\-]+", "_", file_name, flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned)

    # Guarantee batch profession appears in the filename when present.
    if position_slug and position_slug.lower() not in cleaned.lower():
        if re.search(r"-\d+CVs\.xlsx$", cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(
                r"-(\d+CVs\.xlsx)$",
                rf"-{position_slug}-\1",
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            base, ext = os.path.splitext(cleaned)
            cleaned = f"{base}-{position_slug}{ext or '.xlsx'}"

    return cleaned


def candidate_experience_months(candidate: dict) -> int:
    return resolve_experience_months(candidate)


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
    position: str | None = None,
):
    candidates = load_shortlisted_candidates(batch_id, db=db)

    if not candidates:
        print(f"Export skipped: no shortlisted candidates for batch {batch_id}")
        return None

    batch_profession = " ".join(str(position or "").strip().split())

    # Always prefer the batch's saved hiring position from MySQL.
    owned_db = False
    lookup_db = db
    if lookup_db is None:
        try:
            from app.db_mysql import SessionLocal

            lookup_db = SessionLocal()
            owned_db = True
        except Exception as e:
            print("Batch profession DB open error:", e)
            lookup_db = None

    if lookup_db is not None:
        try:
            row = lookup_db.execute(text("""
                SELECT profession
                FROM upload_batches
                WHERE batch_id = :batch_id
                LIMIT 1
            """), {"batch_id": batch_id}).mappings().first()
            db_profession = " ".join(
                str((row or {}).get("profession") or "").strip().split()
            )
            if db_profession:
                batch_profession = db_profession
        except Exception as e:
            print("Batch profession lookup error:", e)
        finally:
            if owned_db:
                try:
                    lookup_db.close()
                except Exception:
                    pass

    if not batch_profession:
        for candidate in candidates:
            value = (
                candidate.get("batch_profession")
                or candidate.get("target_profession")
                or ""
            )
            if value:
                batch_profession = " ".join(str(value).strip().split())
                break

    print(f"Excel position suffix source: '{batch_profession or '(none)'}'")

    stamp = to_sri_lanka(when) if when else now_sri_lanka()

    if batch_no is None:
        batch_no = get_batch_number_for_day(db, batch_id, when)

    wb = Workbook()
    ws = wb.active
    ws.title = "Shortlisted"

    headers = [
        "No",
        "Position",
        "Name",
        "CV File",
        "Email Address",
        "Contact No",
        "Skills",
        "Total Work Experience (months)",
        "Professional Qualifications",
        "CV Profession",
    ]

    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for index, candidate in enumerate(candidates, start=1):
        months = candidate_experience_months(candidate)

        ws.append([
            index,
            batch_profession
            or candidate.get("batch_profession", "")
            or "",
            candidate.get("name", "") or "",
            candidate.get("file_name", "") or "",
            candidate.get("email", "") or "",
            candidate.get("contact_no", "") or "",
            safe_join(candidate.get("skills", [])),
            months,
            safe_join(candidate.get("qualifications", [])),
            candidate.get("profession", "") or "",
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
    file_name = build_excel_filename(
        cv_count,
        batch_no=batch_no,
        when=stamp,
        position=batch_profession,
    )
    file_name = sanitize_excel_filename(file_name, position=batch_profession)
    file_path = os.path.join(EXPORT_DIR, file_name)

    if os.path.exists(file_path):
        base, ext = os.path.splitext(file_name)
        file_name = f"{base}_{batch_id[:8]}{ext}"
        file_path = os.path.join(EXPORT_DIR, file_name)

    if batch_profession and slug_position(batch_profession).lower() not in file_name.lower():
        raise RuntimeError(
            f"Excel filename missing batch position '{batch_profession}': {file_name}"
        )

    wb.save(file_path)

    print(
        f"Excel generated: {file_name} "
        f"(position='{batch_profession or ''}', "
        f"{len(candidates)} shortlisted row(s), batch total {cv_count} CV(s))"
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
