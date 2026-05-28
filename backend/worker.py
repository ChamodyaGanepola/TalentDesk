import time
from app.db_mysql import SessionLocal
from app.db import cv_collection


def process_jobs():

    db = SessionLocal()

    while True:

        job = db.execute("""
            SELECT id, file_url
            FROM cv_jobs
            WHERE status IN ('Uploaded','Queued')
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()

        if not job:
            time.sleep(3)
            continue

        job_id, file_url = job

        # mark processing
        db.execute("""
            UPDATE cv_jobs
            SET status='Processing'
            WHERE id=%s
        """, (job_id,))
        db.commit()

        try:
            # simulate OCR / parsing
            with open(file_url, "rb") as f:
                raw = f.read().decode("utf-8", errors="ignore")

            # save to MongoDB
            cv_collection.insert_one({
                "job_id": job_id,
                "file_url": file_url,
                "extracted_text": raw,
                "structured_data": {},
                "processed_at": time.time()
            })

            # mark done
            db.execute("""
                UPDATE cv_jobs
                SET status='Done'
                WHERE id=%s
            """, (job_id,))
            db.commit()

        except Exception as e:
            db.execute("""
                UPDATE cv_jobs
                SET status='Failed'
                WHERE id=%s
            """, (job_id,))
            db.commit()

        time.sleep(1)


if __name__ == "__main__":
    process_jobs()