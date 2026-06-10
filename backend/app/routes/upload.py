from fastapi import APIRouter, Depends, UploadFile, File, Form, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats

import os
import uuid
import json
from pathlib import Path
from datetime import datetime, timezone

router = APIRouter()

# =========================
# CONFIG
# =========================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Recommended: PDF only unless DOCX support is added in worker
ALLOWED_EXTENSIONS = {".pdf"}

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


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
# BULK UPLOAD CVs
# =========================
@router.post("/upload/cvs")
async def upload_cvs(
    files: list[UploadFile] = File(...),
    skills: str = Form("[]"),
    qualifications: str = Form("[]"),
    experience_type: str = Form("minimum"),
    experience_value: float = Form(0.0),
    db: Session = Depends(get_db)
):
    uploaded_files = []
    failed_files = []

    parsed_skills = safe_json(skills)
    parsed_qualifications = safe_json(qualifications)

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

    batch_id = str(uuid.uuid4())

    try:
        # =========================
        # CREATE BATCH
        # =========================
        db.execute(text("""
            INSERT INTO upload_batches
            (batch_id, experience_type, experience_value)
            VALUES (:batch_id, :experience_type, :experience_value)
        """), {
            "batch_id": batch_id,
            "experience_type": experience_type,
            "experience_value": experience_value
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
                    "created_at": datetime.now(timezone.utc)
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
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db)
):
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)

    offset = (page - 1) * per_page

    rows = db.execute(text("""
        SELECT id, batch_id, file_name, file_url, status, created_at
        FROM uploads
        ORDER BY created_at DESC
        LIMIT :per_page OFFSET :offset
    """), {
        "per_page": per_page,
        "offset": offset
    }).mappings().all()

    total = db.execute(text("""
        SELECT COUNT(*) as count FROM uploads
    """)).mappings().first()["count"]

    return {
        "data": [
            {
                "id": r["id"],
                "batch_id": r["batch_id"],
                "filename": r["file_name"],
                "file_url": r["file_url"],
                "stored_file": os.path.basename(r["file_url"]),
                "status": r["status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }


# =========================
# STATS
# =========================
@router.get("/upload/stats/total")
def total(db: Session = Depends(get_db)):
    return db.execute(text("""
        SELECT COUNT(*) as count FROM uploads
    """)).mappings().first()


@router.get("/upload/stats/pending")
def pending(db: Session = Depends(get_db)):
    return db.execute(text("""
        SELECT COUNT(*) as count FROM uploads WHERE status='Uploaded'
    """)).mappings().first()


@router.get("/upload/stats/shortlisted")
def shortlisted(db: Session = Depends(get_db)):
    return db.execute(text("""
        SELECT COUNT(*) as count FROM uploads WHERE status='Shortlisted'
    """)).mappings().first()


# =========================
# SHORTLISTED BY BATCH
# =========================
@router.get("/resume/shortlisted/{batch_id}")
def get_shortlisted(batch_id: str, db: Session = Depends(get_db)):
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
@router.get("/resume/export/{batch_id}")
def get_export(batch_id: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT excel_file
        FROM batch_exports
        WHERE batch_id = :batch_id
        ORDER BY id DESC
        LIMIT 1
    """), {
        "batch_id": batch_id
    }).mappings().first()

    return row or {"excel_file": None}


# =========================
# EXCEL LIST
# =========================
@router.get("/batch/excels")
def get_excels(
    page: int = 1,
    per_page: int = 10,
    date: str = Query(None),
    db: Session = Depends(get_db)
):
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)

    offset = (page - 1) * per_page
    params = {
        "per_page": per_page,
        "offset": offset
    }

    sql = """
        SELECT id, batch_id, excel_file, created_at
        FROM batch_exports
    """

    if date:
        sql += " WHERE DATE(created_at) = :date"
        params["date"] = date

    sql += " ORDER BY created_at DESC LIMIT :per_page OFFSET :offset"

    rows = db.execute(text(sql), params).mappings().all()

    count_sql = """
        SELECT COUNT(*) as count
        FROM batch_exports
    """

    count_params = {}

    if date:
        count_sql += " WHERE DATE(created_at) = :date"
        count_params["date"] = date

    total = db.execute(text(count_sql), count_params).mappings().first()["count"]

    return {
        "data": [
            {
                "id": r["id"],
                "batch_id": r["batch_id"],
                "file": r["excel_file"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }