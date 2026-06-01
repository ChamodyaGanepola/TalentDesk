from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats
from datetime import timezone, datetime
import os
import uuid
import json

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# SAFE JSON PARSER
# =========================
def safe_json(value: str):
    try:
        return json.loads(value) if value else []
    except:
        return []


# =========================
# SKILLS MASTER (ADD NEW)
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


# =========================
# QUALIFICATIONS MASTER (ADD NEW)
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


# =========================
# GET SKILLS
# =========================
@router.get("/skills")
def get_skills(db: Session = Depends(get_db)):

    rows = db.execute(text("""
        SELECT name FROM skills ORDER BY name
    """)).mappings().all()

    return [r["name"] for r in rows]


# =========================
# GET QUALIFICATIONS
# =========================
@router.get("/qualifications")
def get_qualifications(db: Session = Depends(get_db)):

    rows = db.execute(text("""
        SELECT name FROM qualifications ORDER BY name
    """)).mappings().all()

    return [r["name"] for r in rows]


# =========================
# BULK UPLOAD CVS
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
    # SAVE SKILLS (AUTO ADD NEW)
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
    # SAVE QUALIFICATIONS (AUTO ADD NEW)
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
    # SAVE FILES
    # =========================
    for file in files:

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

    db.commit()
    await broadcast_stats()

    return {
        "success": True,
        "batch_id": batch_id,
        "count": len(uploaded_files),
        "files": uploaded_files
    }


# =========================
# RECENT UPLOADS
# =========================
@router.get("/upload/recent")
def recent_uploads(db: Session = Depends(get_db)):

    rows = db.execute(text("""
        SELECT id, batch_id, file_name, file_url, status, created_at
        FROM uploads
        ORDER BY created_at DESC
        LIMIT 10
    """)).mappings().all()

    return [
        {
            "id": r["id"],
            "filename": r["file_name"],
            "status": r["status"],
            "created_at": r["created_at"].isoformat()
        }
        for r in rows
    ]


# =========================
# STATS
# =========================
@router.get("/upload/stats/total")
def total(db: Session = Depends(get_db)):
    return db.execute(text("SELECT COUNT(*) as count FROM uploads")).mappings().first()


@router.get("/upload/stats/pending")
def pending(db: Session = Depends(get_db)):
    return db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads
        WHERE status='Uploaded'
    """)).mappings().first()


@router.get("/upload/stats/shortlisted")
def shortlisted(db: Session = Depends(get_db)):
    return db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads
        WHERE status='Shortlisted'
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

@router.get("/batch/excels")
def get_excels(db: Session = Depends(get_db)):

    rows = db.execute(text("""
        SELECT id, batch_id, excel_file, created_at
        FROM batch_exports
        ORDER BY created_at DESC
    """)).mappings().all()

    return [
        {
            "id": r["id"],
            "batch_id": r["batch_id"],
            "file": r["excel_file"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        }
        for r in rows
    ]