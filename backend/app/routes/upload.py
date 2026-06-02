from fastapi import APIRouter, Depends, UploadFile, File, Form, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats

import os
import uuid
import json
from datetime import datetime, timezone

router = APIRouter()

# =========================
# CONFIG
# =========================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

# =========================
# HELPERS
# =========================
def safe_json(value: str):
    try:
        return json.loads(value) if value else []
    except:
        return []

def is_allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS


# =========================
# SKILLS MASTER
# =========================
@router.post("/skills/add")
def add_skill(payload: dict = Body(...), db: Session = Depends(get_db)):

    if not payload.get("name"):
        return {"success": False, "message": "Name required"}

    db.execute(text("""
        INSERT IGNORE INTO skills(name)
        VALUES(:name)
    """), {"name": payload["name"].strip().lower()})

    db.commit()
    return {"success": True}


@router.get("/skills")
def get_skills(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT name FROM skills ORDER BY name")).mappings().all()
    return [r["name"] for r in rows]


# =========================
# QUALIFICATIONS MASTER
# =========================
@router.post("/qualifications/add")
def add_qualification(payload: dict = Body(...), db: Session = Depends(get_db)):

    if not payload.get("name"):
        return {"success": False, "message": "Name required"}

    db.execute(text("""
        INSERT IGNORE INTO qualifications(name)
        VALUES(:name)
    """), {"name": payload["name"].strip().lower()})

    db.commit()
    return {"success": True}


@router.get("/qualifications")
def get_qualifications(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT name FROM qualifications ORDER BY name")).mappings().all()
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

    batch_id = str(uuid.uuid4())

    uploaded_files = []
    failed_files = []

    parsed_skills = safe_json(skills)
    parsed_qualifications = safe_json(qualifications)

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
        row = db.execute(text("""
            SELECT id FROM skills WHERE name=:name
        """), {"name": skill.strip().lower()}).fetchone()

        if row:
            db.execute(text("""
                INSERT INTO batch_skills(batch_id, skill_id)
                VALUES(:batch_id, :skill_id)
            """), {
                "batch_id": batch_id,
                "skill_id": row[0]
            })

    # =========================
    # SAVE QUALIFICATIONS
    # =========================
    for q in parsed_qualifications:
        row = db.execute(text("""
            SELECT id FROM qualifications WHERE name=:name
        """), {"name": q.strip().lower()}).fetchone()

        if row:
            db.execute(text("""
                INSERT INTO batch_qualifications(batch_id, qualification_id)
                VALUES(:batch_id, :qualification_id)
            """), {
                "batch_id": batch_id,
                "qualification_id": row[0]
            })

    # =========================
    # FILE UPLOAD (VALIDATED)
    # =========================
    for file in files:

        # ❌ FILE TYPE CHECK
        if not is_allowed_file(file.filename):
            failed_files.append({
                "file": file.filename,
                "error": "Only PDF, DOC, DOCX allowed"
            })
            continue

        try:
            unique_name = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_name)

            content = await file.read()

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
                "file_name": file.filename,
                "file_url": file_path,
                "created_at": datetime.now(timezone.utc)
            })

            uploaded_files.append(file.filename)

        except Exception as e:
            failed_files.append({
                "file": file.filename,
                "error": str(e)
            })

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


# =========================
# RECENT UPLOADS
# =========================
@router.get("/upload/recent")
def recent_uploads(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):

    offset = (page - 1) * per_page

    rows = db.execute(text("""
        SELECT id, batch_id, file_name, file_url, status, created_at
        FROM uploads
        ORDER BY created_at DESC
        LIMIT :per_page OFFSET :offset
    """), {"per_page": per_page, "offset": offset}).mappings().all()

    total = db.execute(text("SELECT COUNT(*) as count FROM uploads")).mappings().first()["count"]

    return {
        "data": [
            {
                "id": r["id"],
                "filename": r["file_name"],
                "file_url": r["file_url"],
                "stored_file": r["file_url"].split("/")[-1],
                "status": r["status"],
                "created_at": r["created_at"].isoformat()
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
    return db.execute(text("SELECT COUNT(*) as count FROM uploads")).mappings().first()

@router.get("/upload/stats/pending")
def pending(db: Session = Depends(get_db)):
    return db.execute(text("SELECT COUNT(*) as count FROM uploads WHERE status='Uploaded'")).mappings().first()

@router.get("/upload/stats/shortlisted")
def shortlisted(db: Session = Depends(get_db)):
    return db.execute(text("SELECT COUNT(*) as count FROM uploads WHERE status='Shortlisted'")).mappings().first()


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
    """), {"batch_id": batch_id}).mappings().all()

    return [
        {
            "id": r["id"],
            "name": r["file_name"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat()
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
    """), {"batch_id": batch_id}).mappings().first()

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

    offset = (page - 1) * per_page
    params = {"per_page": per_page, "offset": offset}

    sql = "SELECT id, batch_id, excel_file, created_at FROM batch_exports"

    if date:
        sql += " WHERE DATE(created_at) = :date"
        params["date"] = date

    sql += " ORDER BY created_at DESC LIMIT :per_page OFFSET :offset"

    rows = db.execute(text(sql), params).mappings().all()

    count_sql = "SELECT COUNT(*) as count FROM batch_exports"
    if date:
        count_sql += " WHERE DATE(created_at) = :date"

    total = db.execute(
        text(count_sql),
        {"date": date} if date else {}
    ).mappings().first()["count"]

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