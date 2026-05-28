from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db_mysql import get_db
from app.ws.broadcaster import broadcast_stats

import os
import uuid
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================
# BULK UPLOAD CVS
# =========================================
@router.post("/upload/cvs")
async def upload_cvs(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):

    uploaded = []

    for file in files:

        unique_name = f"{uuid.uuid4()}_{file.filename}"

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
            "batch_id": str(uuid.uuid4()),
            "file_name": file.filename,
            "file_url": file_path,
            "status": "Uploaded",
            "created_at": datetime.utcnow()
        })

        uploaded.append(file.filename)

    db.commit()

    await broadcast_stats()

    return {
        "success": True,
        "count": len(uploaded),
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
            "created_at": row["created_at"]
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