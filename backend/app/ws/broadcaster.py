from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.ws.manager import manager


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

        shortlisted = db.execute(text("""
            SELECT COUNT(*) FROM uploads WHERE status='Shortlisted'
        """)).fetchone()[0]

    finally:
        db.close()

    await manager.broadcast({
        "event": "stats_update",
        "total": total,
        "pending": pending,
        "shortlisted": shortlisted
    })