from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats
from datetime import timezone, datetime
import os
import uuid
from fastapi import  APIRouter, Depends, UploadFile, File, Form 
import json

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================
# BULK UPLOAD CVS
# =========================================




@router.post("/upload/cvs")
async def upload_cvs(
    files: list[UploadFile] = File(...),

    skills: str = Form(...),

    qualifications: str = Form(...),

    experience_type: str = Form(...),

    experience_value: int = Form(...),

    db: Session = Depends(get_db)
):

    uploaded = []

    batch_id = str(uuid.uuid4())

    parsed_skills = json.loads(skills)

    parsed_qualifications = json.loads(
        qualifications
    )

    # =====================================
    # CREATE BATCH
    # =====================================
    db.execute(text("""
        INSERT INTO upload_batches
        (
            batch_id,
            experience_type,
            experience_value
        )
        VALUES
        (
            :batch_id,
            :experience_type,
            :experience_value
        )
    """), {
        "batch_id": batch_id,
        "experience_type": experience_type,
        "experience_value": experience_value
    })

    # =====================================
    # SAVE SKILLS
    # =====================================
    for skill in parsed_skills:

        existing = db.execute(text("""
            SELECT id
            FROM skills
            WHERE name=:name
        """), {
            "name": skill
        }).mappings().first()

        if existing:
            skill_id = existing["id"]

        else:

            db.execute(text("""
                INSERT INTO skills(name)
                VALUES(:name)
            """), {
                "name": skill
            })

            db.commit()

            created = db.execute(text("""
                SELECT id
                FROM skills
                WHERE name=:name
            """), {
                "name": skill
            }).mappings().first()

            skill_id = created["id"]

        db.execute(text("""
            INSERT INTO batch_skills
            (
                batch_id,
                skill_id
            )
            VALUES
            (
                :batch_id,
                :skill_id
            )
        """), {
            "batch_id": batch_id,
            "skill_id": skill_id
        })

    # =====================================
    # SAVE QUALIFICATIONS
    # =====================================
    for qualification in parsed_qualifications:

        existing = db.execute(text("""
            SELECT id
            FROM qualifications
            WHERE name=:name
        """), {
            "name": qualification
        }).mappings().first()

        if existing:
            qualification_id = existing["id"]

        else:

            db.execute(text("""
                INSERT INTO qualifications(name)
                VALUES(:name)
            """), {
                "name": qualification
            })

            db.commit()

            created = db.execute(text("""
                SELECT id
                FROM qualifications
                WHERE name=:name
            """), {
                "name": qualification
            }).mappings().first()

            qualification_id = created["id"]

        db.execute(text("""
            INSERT INTO batch_qualifications
            (
                batch_id,
                qualification_id
            )
            VALUES
            (
                :batch_id,
                :qualification_id
            )
        """), {
            "batch_id": batch_id,
            "qualification_id": qualification_id
        })

    # =====================================
    # SAVE FILES
    # =====================================
    for file in files:

        unique_name = (
            f"{uuid.uuid4()}_{file.filename}"
        )

        file_path = os.path.join(
            UPLOAD_DIR,
            unique_name
        )

        with open(file_path, "wb") as f:
            f.write(await file.read())

        db.execute(text("""
            INSERT INTO uploads
            (
                batch_id,
                file_name,
                file_url,
                status,
                created_at
            )
            VALUES
            (
                :batch_id,
                :file_name,
                :file_url,
                :status,
                :created_at
            )
        """), {
            "batch_id": batch_id,
            "file_name": file.filename,
            "file_url": file_path,
            "status": "Uploaded",
            "created_at": datetime.now(
                timezone.utc
            )
        })

        uploaded.append(file.filename)

    db.commit()

    await broadcast_stats()

    return {
        "success": True,
        "count": len(uploaded),
        "batch_id": batch_id,
        "files": uploaded
    }



# =========================================
# RECENT UPLOADS
# =========================================
@router.get("/upload/recent")
def recent_uploads(
    db: Session = Depends(get_db)
):

    result = db.execute(text("""
        SELECT
            id,
            batch_id,
            file_name,
            file_url,
            status,
            created_at
        FROM uploads
        ORDER BY created_at DESC
        LIMIT 10
    """)).mappings().all()

    return [
        {
            "id": row["id"],
            "filename": row["file_name"],
            "status": row["status"],
            "created_at": row["created_at"].replace(tzinfo=timezone.utc).isoformat()
        }
        for row in result
    ]


# =========================================
# TOTAL
# =========================================
@router.get("/upload/stats/total")
def total(
    db: Session = Depends(get_db)
):

    result = db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads
    """)).mappings().first()

    return result


# =========================================
# PENDING
# =========================================
@router.get("/upload/stats/pending")
def pending(
    db: Session = Depends(get_db)
):

    result = db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads
        WHERE status='Uploaded'
    """)).mappings().first()

    return result


# =========================================
# SHORTLISTED
# =========================================
@router.get("/upload/stats/shortlisted")
def shortlisted(
    db: Session = Depends(get_db)
):

    result = db.execute(text("""
        SELECT COUNT(*) as count
        FROM uploads
        WHERE status='Shortlisted'
    """)).mappings().first()

    return result