from sqlalchemy import text
from app.db_mysql import SessionLocal
from app.ws.manager import manager


async def broadcast_stats():
    db = SessionLocal()

    try:
        total = db.execute(text("""
            SELECT COUNT(*) FROM uploads
        """)).fetchone()[0]

        pending = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Uploaded'
        """)).fetchone()[0]

        processing = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Processing'
        """)).fetchone()[0]

        shortlisted = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Shortlisted'
        """)).fetchone()[0]

        rejected = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Rejected'
        """)).fetchone()[0]

        failed = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Failed'
        """)).fetchone()[0]

    finally:
        db.close()

    await manager.broadcast({
        "event": "stats_update",
        "total": int(total or 0),
        "pending": int(pending or 0),
        "processing": int(processing or 0),
        "shortlisted": int(shortlisted or 0),
        "rejected": int(rejected or 0),
        "failed": int(failed or 0),
    })