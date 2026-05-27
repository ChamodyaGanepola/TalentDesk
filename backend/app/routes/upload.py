from fastapi import APIRouter, UploadFile, File
import os
import uuid
from datetime import datetime

from app.db import cv_collection
from app.ws.broadcaster import broadcast_stats

router = APIRouter(prefix="/upload")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# UPLOAD CVS
@router.post("/cvs")
async def upload_cvs(files: list[UploadFile] = File(...)):

    if len(files) > 20:
        return {"error": "Max 20 files allowed"}

    saved = []

    for file in files:
        file_id = str(uuid.uuid4())

        file_path = f"{UPLOAD_DIR}/{file_id}_{file.filename}"

        content = await file.read()

        # save file
        with open(file_path, "wb") as f:
            f.write(content)

        # save mongodb
        await cv_collection.insert_one({
            "file_id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "status": "queued",
            "uploaded_at": datetime.utcnow()
        })

        saved.append(file.filename)

    # websocket live update
    await broadcast_stats()

    return {
        "message": "Uploaded successfully",
        "count": len(saved)
    }


# RECENT UPLOADS
@router.get("/recent")
async def recent():

    data = await cv_collection.find() \
        .sort("uploaded_at", -1) \
        .limit(10) \
        .to_list(10)

    for item in data:
        item["_id"] = str(item["_id"])

    return data


# TOTAL COUNT
@router.get("/stats/total")
async def total():

    count = await cv_collection.count_documents({})

    return {"count": count}


# PENDING COUNT
@router.get("/stats/pending")
async def pending():

    count = await cv_collection.count_documents({
        "status": "queued"
    })

    return {"count": count}


# SHORTLISTED COUNT
@router.get("/stats/shortlisted")
async def shortlisted():

    count = await cv_collection.count_documents({
        "status": "shortlisted"
    })

    return {"count": count}