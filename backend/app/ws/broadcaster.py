from app.db import cv_collection
from app.ws.manager import manager


async def broadcast_stats():
    total = await cv_collection.count_documents({})
    pending = await cv_collection.count_documents({"status": "queued"})
    shortlisted = await cv_collection.count_documents({"status": "shortlisted"})

    await manager.broadcast({
        "total": total,
        "pending": pending,
        "shortlisted": shortlisted
    })