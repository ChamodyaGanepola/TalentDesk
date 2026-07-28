from fastapi import APIRouter, Depends, UploadFile, File, Form, Body, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.auth import get_current_user
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats
from app.core.pagination import (
    clamp_page_size,
    decode_cursor,
    encode_cursor,
    parse_cursor_datetime,
    split_keyset_page,
    ensure_pagination_indexes,
)

import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

router = APIRouter(dependencies=[Depends(get_current_user)])


def parse_user_id(user: dict) -> int:
    try:
        return int(user["id"])
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid user session") from e

_indexes_ready = False


def _ensure_indexes(db: Session):
    global _indexes_ready
    if _indexes_ready:
        return
    ensure_pagination_indexes(db)
    _indexes_ready = True

# =========================
# CONFIG
# =========================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Recommended: PDF only unless DOCX support is added in worker
ALLOWED_EXTENSIONS = {".pdf"}

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


from app.services.utils_experience import (
    months_to_label,
    months_to_years_float,
    normalize_requirement_months,
    parse_include_internships,
)


def serialize_batch_experience(experience_value):
    """experience_value in DB is months. Expose months + display label."""
    months = normalize_requirement_months(experience_value)
    return {
        "experience_months": months,
        "experience_value": months,  # months (canonical)
        "experience_label": months_to_label(months),
        "experience_years": months_to_years_float(months),
    }


_experience_migrated = False
_include_internships_ready = False
_profession_schema_ready = False


def ensure_experience_stored_as_months(db: Session):
    """
    One-time: older rows stored years as a float (<= ~40).
    Convert those to months so matching/display stay consistent.
    """
    global _experience_migrated
    if _experience_migrated:
        return

    try:
        row = db.execute(text("""
            SELECT
                COALESCE(MAX(experience_value), 0) AS max_value,
                COUNT(*) AS total
            FROM upload_batches
        """)).mappings().first()

        max_value = float(row["max_value"] or 0)
        total = int(row["total"] or 0)

        # Already using months if any requirement is clearly > 40 months,
        # or there is nothing to migrate.
        if total == 0 or max_value > 40:
            _experience_migrated = True
            return

        db.execute(text("""
            UPDATE upload_batches
            SET experience_value = ROUND(experience_value * 12)
            WHERE experience_value IS NOT NULL
        """))
        db.commit()
        print("Migrated upload_batches.experience_value from years to months")
    except Exception as e:
        print("Experience months migration skipped:", e)
        try:
            db.rollback()
        except Exception:
            pass

    _experience_migrated = True


def ensure_include_internships_column(db: Session):
    """Add upload_batches.include_internships if missing (default include=1)."""
    global _include_internships_ready
    if _include_internships_ready:
        return

    try:
        db.execute(text("""
            ALTER TABLE upload_batches
            ADD COLUMN include_internships TINYINT(1) NOT NULL DEFAULT 1
        """))
        db.commit()
        print("Added upload_batches.include_internships column")
    except Exception as e:
        # Column already exists (or non-MySQL) — safe to continue.
        print("include_internships column ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    try:
        db.execute(text("""
            ALTER TABLE upload_batches
            ADD COLUMN intern_label VARCHAR(255) NULL
        """))
        db.commit()
        print("Added upload_batches.intern_label column")
    except Exception as e:
        print("intern_label column ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    _include_internships_ready = True


_failure_reason_ready = False


def ensure_failure_reason_column(db: Session):
    """Add uploads.failure_reason for rejected/failed CV explanations."""
    global _failure_reason_ready
    if _failure_reason_ready:
        return

    try:
        db.execute(text("""
            ALTER TABLE uploads
            ADD COLUMN failure_reason VARCHAR(500) NULL
        """))
        db.commit()
        print("Added uploads.failure_reason column")
    except Exception as e:
        print("failure_reason column ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    _failure_reason_ready = True


_batch_user_ready = False


def ensure_batch_user_isolation(db: Session):
    """
    Scope batches (and thus uploads/exports) to a user.
    Existing rows are assigned to the oldest user currently in the DB.
    """
    global _batch_user_ready
    if _batch_user_ready:
        return

    try:
        col = db.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'upload_batches'
              AND COLUMN_NAME = 'user_id'
        """)).scalar()

        if int(col or 0) == 0:
            db.execute(text("""
                ALTER TABLE upload_batches
                ADD COLUMN user_id INT NULL
            """))
            db.commit()
            print("Added upload_batches.user_id column")
    except Exception as e:
        print("upload_batches.user_id ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    try:
        owner_id = db.execute(text("""
            SELECT id FROM users
            ORDER BY id ASC
            LIMIT 1
        """)).scalar()

        if owner_id is not None:
            db.execute(text("""
                UPDATE upload_batches
                SET user_id = :user_id
                WHERE user_id IS NULL
            """), {"user_id": int(owner_id)})
            db.commit()
            print(f"Backfilled upload_batches.user_id -> user {owner_id}")

            try:
                db.execute(text("""
                    ALTER TABLE upload_batches
                    MODIFY COLUMN user_id INT NOT NULL
                """))
                db.commit()
            except Exception as e:
                print("upload_batches.user_id NOT NULL ensure:", e)
                try:
                    db.rollback()
                except Exception:
                    pass
        else:
            print("No users found to own existing batches; user_id left nullable")
    except Exception as e:
        print("upload_batches.user_id backfill:", e)
        try:
            db.rollback()
        except Exception:
            pass

    try:
        idx = db.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'upload_batches'
              AND INDEX_NAME = 'idx_upload_batches_user_created'
        """)).scalar()
        if int(idx or 0) == 0:
            db.execute(text("""
                CREATE INDEX idx_upload_batches_user_created
                ON upload_batches (user_id, created_at)
            """))
            db.commit()
    except Exception as e:
        print("upload_batches user index ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    _batch_user_ready = True


def user_owns_batch(db: Session, batch_id: str, user_id: int) -> bool:
    ensure_batch_user_isolation(db)
    row = db.execute(text("""
        SELECT 1
        FROM upload_batches
        WHERE batch_id = :batch_id
          AND user_id = :user_id
        LIMIT 1
    """), {
        "batch_id": batch_id,
        "user_id": user_id,
    }).fetchone()
    return row is not None


def require_batch_owner(db: Session, batch_id: str, user_id: int) -> None:
    if not user_owns_batch(db, batch_id, user_id):
        raise HTTPException(status_code=404, detail="Batch not found")


def ensure_profession_schema(db: Session):
    """Professions master list + optional batch position name."""
    global _profession_schema_ready
    if _profession_schema_ready:
        return

    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS professions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                UNIQUE KEY uq_professions_name (name)
            )
        """))
        db.commit()
    except Exception as e:
        print("professions table ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    try:
        col = db.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'upload_batches'
              AND COLUMN_NAME = 'profession'
        """)).scalar()

        if int(col or 0) == 0:
            db.execute(text("""
                ALTER TABLE upload_batches
                ADD COLUMN profession VARCHAR(255) NULL
            """))
            db.commit()
            print("Added upload_batches.profession column")
    except Exception as e:
        print("profession column ensure:", e)
        try:
            db.rollback()
        except Exception:
            pass

    try:
        exists = db.execute(text("""
            SELECT COUNT(*) AS cnt
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'professions'
        """)).scalar()
        _profession_schema_ready = int(exists or 0) > 0
        if _profession_schema_ready:
            print("Professions master table ready")
        else:
            print("Professions master table missing after ensure")
    except Exception as e:
        print("professions schema check failed:", e)
        try:
            db.rollback()
        except Exception:
            pass
        _profession_schema_ready = False


# =========================
# HELPERS
# =========================
def safe_json(value: str):
    try:
        parsed = json.loads(value) if value else []
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def is_allowed_file(filename: str) -> bool:
    if not filename:
        return False

    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS


def clean_name(value: str) -> str:
    return str(value or "").strip().lower()


def safe_filename(filename: str) -> str:
    original_name = Path(filename).name
    return original_name.replace("\\", "_").replace("/", "_")


def get_or_create_skill(db: Session, name: str):
    name = clean_name(name)
    if not name:
        return None

    db.execute(text("""
        INSERT IGNORE INTO skills(name)
        VALUES(:name)
    """), {"name": name})

    row = db.execute(text("""
        SELECT id FROM skills WHERE name=:name
    """), {"name": name}).fetchone()

    return row[0] if row else None


def get_or_create_qualification(db: Session, name: str):
    name = clean_name(name)
    if not name:
        return None

    db.execute(text("""
        INSERT IGNORE INTO qualifications(name)
        VALUES(:name)
    """), {"name": name})

    row = db.execute(text("""
        SELECT id FROM qualifications WHERE name=:name
    """), {"name": name}).fetchone()

    return row[0] if row else None


def normalize_profession(value: str) -> str:
    """Preserve readable casing; collapse whitespace."""
    return " ".join(str(value or "").strip().split())


def get_or_create_profession(db: Session, name: str) -> str | None:
    name = normalize_profession(name)
    if not name:
        return None

    ensure_profession_schema(db)

    existing = db.execute(text("""
        SELECT name FROM professions
        WHERE LOWER(name) = LOWER(:name)
        LIMIT 1
    """), {"name": name}).fetchone()

    if existing:
        return existing[0]

    db.execute(text("""
        INSERT IGNORE INTO professions(name)
        VALUES(:name)
    """), {"name": name})

    row = db.execute(text("""
        SELECT name FROM professions
        WHERE LOWER(name) = LOWER(:name)
        LIMIT 1
    """), {"name": name}).fetchone()

    return row[0] if row else name


# =========================
# SKILLS MASTER
# =========================
@router.post("/skills/add")
def add_skill(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = clean_name(payload.get("name"))

    if not name:
        return {"success": False, "message": "Name required"}

    db.execute(text("""
        INSERT IGNORE INTO skills(name)
        VALUES(:name)
    """), {"name": name})

    db.commit()

    return {"success": True}


@router.get("/skills")
def get_skills(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT name FROM skills ORDER BY name
    """)).mappings().all()

    return [r["name"] for r in rows]


# =========================
# QUALIFICATIONS MASTER
# =========================
@router.post("/qualifications/add")
def add_qualification(payload: dict = Body(...), db: Session = Depends(get_db)):
    name = clean_name(payload.get("name"))

    if not name:
        return {"success": False, "message": "Name required"}

    db.execute(text("""
        INSERT IGNORE INTO qualifications(name)
        VALUES(:name)
    """), {"name": name})

    db.commit()

    return {"success": True}


@router.get("/qualifications")
def get_qualifications(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT name FROM qualifications ORDER BY name
    """)).mappings().all()

    return [r["name"] for r in rows]


# =========================
# PROFESSIONS MASTER (info only — not used in matching)
# =========================
@router.post("/professions/add")
def add_profession(payload: dict = Body(...), db: Session = Depends(get_db)):
    try:
        ensure_profession_schema(db)
        name = get_or_create_profession(db, payload.get("name"))

        if not name:
            return {"success": False, "message": "Name required"}

        db.commit()
        return {"success": True, "name": name}
    except Exception as e:
        print("add_profession error:", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "success": False,
            "message": "Could not save profession. Please try again.",
        }


@router.get("/professions")
def get_professions(db: Session = Depends(get_db)):
    ensure_profession_schema(db)

    try:
        rows = db.execute(text("""
            SELECT name FROM professions ORDER BY name
        """)).mappings().all()
        return [r["name"] for r in rows]
    except Exception as e:
        print("get_professions error:", e)
        try:
            db.rollback()
        except Exception:
            pass
        return []


# =========================
# BULK UPLOAD CVs
# =========================
@router.post("/upload/cvs")
async def upload_cvs(
    files: list[UploadFile] = File(...),
    skills: str = Form("[]"),
    qualifications: str = Form("[]"),
    experience_type: str = Form("minimum"),
    experience_value: float = Form(0.0),
    experience_months: int | None = Form(None),
    include_internships: str = Form("yes"),
    profession: str = Form(""),
    intern_label: str = Form(""),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    uploaded_files = []
    failed_files = []
    user_id = parse_user_id(user)

    parsed_skills = safe_json(skills)
    parsed_qualifications = safe_json(qualifications)
    include_internships_flag = parse_include_internships(include_internships)
    batch_profession = normalize_profession(profession)
    batch_intern_label = " ".join(str(intern_label or "").strip().split())

    valid_experience_types = {"minimum", "more_than", "exact"}

    if experience_type not in valid_experience_types:
        return {
            "success": False,
            "message": "Invalid experience type",
            "allowed": list(valid_experience_types)
        }

    if not files:
        return {
            "success": False,
            "message": "No files uploaded"
        }

    # Canonical storage unit: months.
    # Prefer experience_months from the updated frontend.
    if experience_months is not None:
        stored_months = max(int(experience_months), 0)
    else:
        # Legacy clients sent years as a float in experience_value only.
        from app.services.utils_experience import years_to_months
        stored_months = years_to_months(experience_value)

    batch_id = str(uuid.uuid4())

    try:
        ensure_experience_stored_as_months(db)
        ensure_include_internships_column(db)
        ensure_profession_schema(db)
        ensure_batch_user_isolation(db)

        if batch_profession:
            batch_profession = get_or_create_profession(db, batch_profession) or batch_profession

        # =========================
        # CREATE BATCH
        # =========================
        db.execute(text("""
            INSERT INTO upload_batches
            (batch_id, user_id, experience_type, experience_value, include_internships, profession, intern_label, created_at)
            VALUES (
                :batch_id,
                :user_id,
                :experience_type,
                :experience_value,
                :include_internships,
                :profession,
                :intern_label,
                :created_at
            )
        """), {
            "batch_id": batch_id,
            "user_id": user_id,
            "experience_type": experience_type,
            "experience_value": stored_months,
            "include_internships": 1 if include_internships_flag else 0,
            "profession": batch_profession or None,
            "intern_label": batch_intern_label or None,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None)
        })

        # =========================
        # SAVE SKILLS
        # =========================
        for skill in parsed_skills:
            skill_id = get_or_create_skill(db, skill)

            if skill_id:
                db.execute(text("""
                    INSERT INTO batch_skills(batch_id, skill_id)
                    VALUES(:batch_id, :skill_id)
                """), {
                    "batch_id": batch_id,
                    "skill_id": skill_id
                })

        # =========================
        # SAVE QUALIFICATIONS
        # =========================
        for qualification in parsed_qualifications:
            qualification_id = get_or_create_qualification(db, qualification)

            if qualification_id:
                db.execute(text("""
                    INSERT INTO batch_qualifications(batch_id, qualification_id)
                    VALUES(:batch_id, :qualification_id)
                """), {
                    "batch_id": batch_id,
                    "qualification_id": qualification_id
                })

        # =========================
        # FILE UPLOAD
        # =========================
        for file in files:
            if not is_allowed_file(file.filename):
                failed_files.append({
                    "file": file.filename,
                    "error": "Only PDF files are allowed"
                })
                continue

            try:
                original_name = safe_filename(file.filename)
                unique_name = f"{uuid.uuid4()}_{original_name}"
                file_path = os.path.join(UPLOAD_DIR, unique_name)

                content = await file.read()

                if len(content) > MAX_FILE_SIZE_BYTES:
                    failed_files.append({
                        "file": file.filename,
                        "error": f"File size exceeds {MAX_FILE_SIZE_MB} MB"
                    })
                    continue

                if len(content) == 0:
                    failed_files.append({
                        "file": file.filename,
                        "error": "Empty file"
                    })
                    continue

                with open(file_path, "wb") as f:
                    f.write(content)

                db.execute(text("""
                    INSERT INTO uploads(
                        batch_id,
                        file_name,
                        file_url,
                        status,
                        created_at
                    )
                    VALUES(
                        :batch_id,
                        :file_name,
                        :file_url,
                        'Uploaded',
                        :created_at
                    )
                """), {
                    "batch_id": batch_id,
                    "file_name": original_name,
                    "file_url": file_path,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None)
                })

                uploaded_files.append(original_name)

            except Exception as e:
                failed_files.append({
                    "file": file.filename,
                    "error": str(e)
                })

        if len(uploaded_files) == 0:
            db.rollback()
            return {
                "success": False,
                "message": "No valid files uploaded",
                "batch_id": None,
                "uploaded": 0,
                "failed": len(failed_files),
                "uploaded_files": [],
                "failed_files": failed_files
            }

        db.commit()
        await broadcast_stats()

        return {
            "success": len(failed_files) == 0,
            "batch_id": batch_id,
            "uploaded": len(uploaded_files),
            "failed": len(failed_files),
            "uploaded_files": uploaded_files,
            "failed_files": failed_files
        }

    except Exception as e:
        db.rollback()

        return {
            "success": False,
            "message": "Upload failed",
            "error": str(e),
            "batch_id": None,
            "uploaded": 0,
            "failed": len(files),
            "uploaded_files": [],
            "failed_files": failed_files
        }


# =========================
# RECENT UPLOADS
# =========================
@router.get("/upload/recent")
def recent_uploads(
    cursor: str | None = Query(None),
    per_page: int = 10,
    batch_id: str | None = Query(None),
    date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Keyset-paginated recent uploads (default 10/page).
    Cursor is opaque; ordered by created_at DESC, id DESC.
    """
    _ensure_indexes(db)
    ensure_failure_reason_column(db)
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)

    page_size = clamp_page_size(per_page)
    fetch_limit = page_size + 1

    where_parts = ["ub.user_id = :user_id"]
    params: dict = {"fetch_limit": fetch_limit, "user_id": user_id}

    if batch_id:
        require_batch_owner(db, batch_id, user_id)
        where_parts.append("u.batch_id = :batch_id")
        params["batch_id"] = batch_id

    if date:
        where_parts.append(
            "DATE(DATE_ADD(u.created_at, INTERVAL 330 MINUTE)) = :date"
        )
        params["date"] = date

    cursor_data = decode_cursor(cursor)
    if cursor_data:
        cursor_created = parse_cursor_datetime(cursor_data.get("created_at"))
        cursor_id = cursor_data.get("id")
        if cursor_created is not None and cursor_id is not None:
            where_parts.append("""
                (
                    u.created_at < :cursor_created
                    OR (u.created_at = :cursor_created AND u.id < :cursor_id)
                )
            """)
            params["cursor_created"] = cursor_created
            params["cursor_id"] = int(cursor_id)

    where_sql = " AND ".join(where_parts)

    rows = db.execute(text(f"""
        SELECT u.id, u.batch_id, u.file_name, u.file_url, u.status, u.failure_reason, u.created_at
        FROM uploads u
        INNER JOIN upload_batches ub ON ub.batch_id = u.batch_id
        WHERE {where_sql}
        ORDER BY u.created_at DESC, u.id DESC
        LIMIT :fetch_limit
    """), params).mappings().all()

    items, has_more = split_keyset_page(list(rows), page_size)

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({
            "id": last["id"],
            "created_at": last["created_at"].isoformat() if last["created_at"] else None,
        })

    def _reason_for_row(row) -> str:
        reason = str(row.get("failure_reason") or "").strip()
        status = str(row.get("status") or "")
        if reason:
            return reason
        if status == "Rejected":
            return "Did not meet screening criteria"
        if status == "Failed":
            return "Processing failed"
        return ""

    return {
        "data": [
            {
                "id": r["id"],
                "batch_id": r["batch_id"],
                "filename": r["file_name"],
                "file_url": r["file_url"],
                "stored_file": os.path.basename(r["file_url"]),
                "status": r["status"],
                "failure_reason": _reason_for_row(r),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in items
        ],
        "per_page": page_size,
        "has_more": has_more,
        "next_cursor": next_cursor,
    }


# =========================
# STATS
# =========================
@router.get("/upload/stats/total")
def total(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)
    return db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads u
        INNER JOIN upload_batches ub ON ub.batch_id = u.batch_id
        WHERE ub.user_id = :user_id
    """), {"user_id": user_id}).mappings().first()


@router.get("/upload/stats/pending")
def pending(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)
    return db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads u
        INNER JOIN upload_batches ub ON ub.batch_id = u.batch_id
        WHERE ub.user_id = :user_id
          AND u.status='Uploaded'
    """), {"user_id": user_id}).mappings().first()


@router.get("/upload/stats/shortlisted")
def shortlisted(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)
    return db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads u
        INNER JOIN upload_batches ub ON ub.batch_id = u.batch_id
        WHERE ub.user_id = :user_id
          AND u.status='Shortlisted'
    """), {"user_id": user_id}).mappings().first()


# =========================
# SHORTLISTED BY BATCH
# =========================
@router.get("/resume/shortlisted/{batch_id}")
def get_shortlisted(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    require_batch_owner(db, batch_id, parse_user_id(user))
    rows = db.execute(text("""
        SELECT *
        FROM uploads
        WHERE batch_id = :batch_id
        AND status = 'Shortlisted'
        ORDER BY created_at DESC
    """), {
        "batch_id": batch_id
    }).mappings().all()

    return [
        {
            "id": r["id"],
            "name": r["file_name"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        }
        for r in rows
    ]


# =========================
# EXPORT
# =========================
def _persist_export_result(db: Session, batch_id: str, export_result: dict) -> dict:
    existing = db.execute(text("""
        SELECT id FROM batch_exports
        WHERE batch_id = :batch_id
        ORDER BY id DESC
        LIMIT 1
    """), {"batch_id": batch_id}).fetchone()

    if existing:
        db.execute(text("""
            UPDATE batch_exports
            SET excel_file=:excel_file, created_at=:created_at
            WHERE id=:id
        """), {
            "excel_file": export_result["file_path"],
            "created_at": export_result["generated_at"],
            "id": existing[0],
        })
    else:
        db.execute(text("""
            INSERT INTO batch_exports(batch_id, excel_file, created_at)
            VALUES(:batch_id, :excel_file, :created_at)
        """), {
            "batch_id": batch_id,
            "excel_file": export_result["file_path"],
            "created_at": export_result["generated_at"],
        })

    db.commit()

    return {
        "success": True,
        "excel_file": export_result["file_path"],
        "excel_name": export_result["file_name"],
        "created_at": export_result["generated_at"].isoformat(),
        "generated_at_sl": export_result.get("generated_at_sl"),
    }


def _generate_batch_export(db: Session, batch_id: str) -> dict | None:
    from app.services.export_service import export_batch_shortlisted

    total_count = db.execute(text("""
        SELECT COUNT(*) FROM uploads WHERE batch_id = :batch_id
    """), {"batch_id": batch_id}).scalar() or 0

    batch_profession = ""
    try:
        batch_profession = str(
            db.execute(text("""
                SELECT profession FROM upload_batches
                WHERE batch_id = :batch_id LIMIT 1
            """), {"batch_id": batch_id}).scalar()
            or ""
        ).strip()
    except Exception:
        batch_profession = ""

    return export_batch_shortlisted(
        batch_id,
        total_cvs=total_count,
        db=db,
        position=batch_profession,
    )


@router.get("/resume/export/{batch_id}")
def get_export(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return export path, regenerating so format/content stay current."""
    require_batch_owner(db, batch_id, parse_user_id(user))

    export_result = _generate_batch_export(db, batch_id)
    if export_result:
        saved = _persist_export_result(db, batch_id, export_result)
        return {
            "excel_file": saved["excel_file"],
            "created_at": saved["created_at"],
            "excel_name": saved.get("excel_name"),
        }

    row = db.execute(text("""
        SELECT excel_file, created_at
        FROM batch_exports
        WHERE batch_id = :batch_id
        ORDER BY id DESC
        LIMIT 1
    """), {
        "batch_id": batch_id
    }).mappings().first()

    if not row:
        return {"excel_file": None, "created_at": None}

    return {
        "excel_file": row["excel_file"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.post("/resume/export/{batch_id}/regenerate")
def regenerate_export(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    require_batch_owner(db, batch_id, parse_user_id(user))

    export_result = _generate_batch_export(db, batch_id)

    if not export_result:
        return {
            "success": False,
            "message": "No shortlisted candidates to export",
            "excel_file": None,
        }

    return _persist_export_result(db, batch_id, export_result)


# =========================
# EXCEL LIST
# =========================
@router.get("/batch/excels")
def get_excels(
    cursor: str | None = Query(None),
    per_page: int = 10,
    date: str = Query(None),
    batch_id: str = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Keyset-paginated Excel exports (default 10/page), ordered by id DESC."""
    _ensure_indexes(db)
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)

    page_size = clamp_page_size(per_page)
    fetch_limit = page_size + 1

    where_parts = ["ub.user_id = :user_id"]
    params: dict = {"fetch_limit": fetch_limit, "user_id": user_id}

    if date:
        where_parts.append(
            "DATE(DATE_ADD(be.created_at, INTERVAL 330 MINUTE)) = :date"
        )
        params["date"] = date

    if batch_id:
        require_batch_owner(db, batch_id, user_id)
        where_parts.append("be.batch_id = :batch_id")
        params["batch_id"] = batch_id

    cursor_data = decode_cursor(cursor)
    if cursor_data and cursor_data.get("id") is not None:
        where_parts.append("be.id < :cursor_id")
        params["cursor_id"] = int(cursor_data["id"])

    where_sql = f" WHERE {' AND '.join(where_parts)}"

    sql = f"""
        SELECT be.id, be.batch_id, be.excel_file, be.created_at
        FROM batch_exports be
        INNER JOIN upload_batches ub ON ub.batch_id = be.batch_id
        {where_sql}
        ORDER BY be.id DESC
        LIMIT :fetch_limit
    """

    rows = db.execute(text(sql), params).mappings().all()
    items, has_more = split_keyset_page(list(rows), page_size)

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({"id": last["id"]})

    return {
        "data": [
            {
                "id": r["id"],
                "batch_id": r["batch_id"],
                "file": r["excel_file"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in items
        ],
        "per_page": page_size,
        "has_more": has_more,
        "next_cursor": next_cursor,
    }
    
@router.get("/upload/stats/all")
def all_stats(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)
    row = db.execute(text("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN u.status='Uploaded' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN u.status='Processing' THEN 1 ELSE 0 END) AS processing,
            SUM(CASE WHEN u.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
            SUM(CASE WHEN u.status='Rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN u.status='Failed' THEN 1 ELSE 0 END) AS failed
        FROM uploads u
        INNER JOIN upload_batches ub ON ub.batch_id = u.batch_id
        WHERE ub.user_id = :user_id
    """), {"user_id": user_id}).mappings().first()

    return {
        "total": row["total"] or 0,
        "pending": row["pending"] or 0,
        "processing": row["processing"] or 0,
        "shortlisted": row["shortlisted"] or 0,
        "rejected": row["rejected"] or 0,
        "failed": row["failed"] or 0,
    }
@router.get("/upload/batches")
def get_batches(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ensure_experience_stored_as_months(db)
    ensure_include_internships_column(db)
    ensure_profession_schema(db)
    ensure_batch_user_isolation(db)
    user_id = parse_user_id(user)

    rows = db.execute(text("""
        SELECT
            ub.batch_id,
            ub.experience_type,
            ub.experience_value,
            ub.include_internships,
            ub.profession,
            ub.intern_label,
            COALESCE(ub.created_at, MIN(u.created_at)) AS created_at,
            COUNT(u.id) AS total,
            SUM(CASE WHEN u.status='Uploaded' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN u.status='Processing' THEN 1 ELSE 0 END) AS processing,
            SUM(CASE WHEN u.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
            SUM(CASE WHEN u.status='Rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN u.status='Failed' THEN 1 ELSE 0 END) AS failed
        FROM upload_batches ub
        LEFT JOIN uploads u ON u.batch_id = ub.batch_id
        WHERE ub.user_id = :user_id
        GROUP BY ub.batch_id, ub.experience_type, ub.experience_value, ub.include_internships, ub.profession, ub.intern_label, ub.created_at
        ORDER BY COALESCE(ub.created_at, MIN(u.created_at)) DESC
    """), {"user_id": user_id}).mappings().all()

    return [
        {
            "batch_id": r["batch_id"],
            "experience_type": r["experience_type"],
            "include_internships": parse_include_internships(r["include_internships"]),
            "profession": r["profession"] or "",
            "intern_label": r["intern_label"] or "",
            **serialize_batch_experience(r["experience_value"]),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "total": r["total"] or 0,
            "pending": r["pending"] or 0,
            "processing": r["processing"] or 0,
            "shortlisted": r["shortlisted"] or 0,
            "rejected": r["rejected"] or 0,
            "failed": r["failed"] or 0,
        }
        for r in rows
    ]

# =========================
# BATCH DETAILS
# =========================
@router.get("/upload/batch/{batch_id}")
def get_batch_details(
    batch_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ensure_experience_stored_as_months(db)
    ensure_include_internships_column(db)
    ensure_profession_schema(db)
    ensure_failure_reason_column(db)
    require_batch_owner(db, batch_id, parse_user_id(user))

    batch = db.execute(text("""
        SELECT
            ub.batch_id,
            ub.experience_type,
            ub.experience_value,
            ub.include_internships,
            ub.profession,
            ub.intern_label,
            COALESCE(ub.created_at, MIN(u.created_at)) AS created_at,
            COUNT(u.id) AS total,
            SUM(CASE WHEN u.status='Uploaded' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN u.status='Processing' THEN 1 ELSE 0 END) AS processing,
            SUM(CASE WHEN u.status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
            SUM(CASE WHEN u.status='Rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN u.status='Failed' THEN 1 ELSE 0 END) AS failed
        FROM upload_batches ub
        LEFT JOIN uploads u ON u.batch_id = ub.batch_id
        WHERE ub.batch_id = :batch_id
        GROUP BY ub.batch_id, ub.experience_type, ub.experience_value, ub.include_internships, ub.profession, ub.intern_label, ub.created_at
    """), {
        "batch_id": batch_id
    }).mappings().first()

    if not batch:
        return {
            "success": False,
            "message": "Batch not found"
        }

    skills = db.execute(text("""
        SELECT s.name
        FROM batch_skills bs
        JOIN skills s ON s.id = bs.skill_id
        WHERE bs.batch_id = :batch_id
        ORDER BY s.name
    """), {
        "batch_id": batch_id
    }).mappings().all()

    qualifications = db.execute(text("""
        SELECT q.name
        FROM batch_qualifications bq
        JOIN qualifications q ON q.id = bq.qualification_id
        WHERE bq.batch_id = :batch_id
        ORDER BY q.name
    """), {
        "batch_id": batch_id
    }).mappings().all()

    uploads = db.execute(text("""
        SELECT
            id,
            batch_id,
            file_name,
            file_url,
            status,
            failure_reason,
            created_at
        FROM uploads
        WHERE batch_id = :batch_id
        ORDER BY created_at DESC
    """), {
        "batch_id": batch_id
    }).mappings().all()

    export_row = db.execute(text("""
        SELECT excel_file, created_at
        FROM batch_exports
        WHERE batch_id = :batch_id
        ORDER BY id DESC
        LIMIT 1
    """), {
        "batch_id": batch_id
    }).mappings().first()

    excel_file = None
    excel_created_at = None
    if export_row and export_row.get("excel_file"):
        excel_file = str(export_row["excel_file"]).replace("\\", "/")
        if export_row.get("created_at"):
            excel_created_at = export_row["created_at"].isoformat()

    return {
        "success": True,
        "batch": {
            "batch_id": batch["batch_id"],
            "experience_type": batch["experience_type"],
            "include_internships": parse_include_internships(
                batch.get("include_internships")
            ),
            "profession": batch.get("profession") or "",
            "intern_label": batch.get("intern_label") or "",
            **serialize_batch_experience(batch["experience_value"]),
            "created_at": batch["created_at"].isoformat() if batch["created_at"] else None,
            "total": batch["total"] or 0,
            "pending": batch["pending"] or 0,
            "processing": batch["processing"] or 0,
            "shortlisted": batch["shortlisted"] or 0,
            "rejected": batch["rejected"] or 0,
            "failed": batch["failed"] or 0,
            "skills": [s["name"] for s in skills],
            "qualifications": [q["name"] for q in qualifications],
            "excel_file": excel_file,
            "excel_name": os.path.basename(excel_file) if excel_file else None,
            "excel_created_at": excel_created_at,
        },
        "uploads": [
            {
                "id": u["id"],
                "batch_id": u["batch_id"],
                "filename": u["file_name"],
                "file_url": u["file_url"],
                "stored_file": os.path.basename(u["file_url"]),
                "status": u["status"],
                "failure_reason": (
                    str(u.get("failure_reason") or "").strip()
                    or (
                        "Did not meet screening criteria"
                        if str(u.get("status") or "") == "Rejected"
                        else "Processing failed"
                        if str(u.get("status") or "") == "Failed"
                        else ""
                    )
                ),
                "created_at": u["created_at"].isoformat() if u["created_at"] else None
            }
            for u in uploads
        ]
    }   