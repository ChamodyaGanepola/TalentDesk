import time
import os
from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db.mongo import cv_collection
from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text

from PyPDF2 import PdfReader


# =========================================
# SHORTLIST LOGIC
# =========================================
def is_shortlisted(ai_result: str) -> bool:
    ai_result = str(ai_result).lower()
    required_skills = ["python", "fastapi", "react"]
    return any(skill in ai_result for skill in required_skills)


# =========================================
# READ FILE
# =========================================
def read_file(file_path: str) -> str:
    try:
        if not os.path.exists(file_path):
            print("❌ File not found:", file_path)
            return ""

        if file_path.lower().endswith(".pdf"):
            print("📄 Reading PDF:", file_path)

            reader = PdfReader(file_path)
            text_content = ""

            for page in reader.pages:
                text_content += page.extract_text() or ""

            print("📄 PDF extracted length:", len(text_content))
            return text_content

        else:
            print("📄 Reading TEXT file:", file_path)
            with open(file_path, "r", errors="ignore") as f:
                content = f.read()

            print("📄 Text length:", len(content))
            return content

    except Exception as e:
        print("❌ File read error:", e)
        return ""


# =========================================
# WORKER
# =========================================
def process_jobs():

    db = SessionLocal()
    print("🚀 Worker started... waiting for jobs")

    while True:

        print("\n🔎 Checking for new CV job...")

        job = db.execute(text("""
            SELECT id, batch_id, file_url, file_name
            FROM uploads
            WHERE LOWER(status) = 'uploaded'
            ORDER BY id ASC
            LIMIT 1
        """)).fetchone()

        if not job:
            print("⏳ No jobs found. Sleeping...")
            time.sleep(2)
            continue

        job_id, batch_id, file_url, file_name = job

        print(f"\n📥 New Job Found: {file_name}")
        print("🆔 Job ID:", job_id)

        # =====================================
        # MARK PROCESSING
        # =====================================
        print("⚙️ Marking as Processing...")
        db.execute(text("""
            UPDATE uploads
            SET status = 'Processing'
            WHERE id = :id
        """), {"id": job_id})
        db.commit()

        try:

            # =====================================
            # READ FILE
            # =====================================
            print("📂 Reading file...")
            content = read_file(file_url)

            if not content:
                raise Exception("Empty or unreadable file")

            print("📊 Content length:", len(content))

            # =====================================
            # CHOOSE ENGINE
            # =====================================
            if len(content) < 20000:

                print("🧠 Using VISION OCR (PDF → Image → GPT-4o)")
                method = "openai_vision_ocr"

                ai_result = vision_ocr(file_url)

            else:

                print("🧠 Using TEXT AI extraction")
                method = "openai_text"

                ai_result = extract_cv_text(content)

            print("✅ AI extraction done")

            # =====================================
            # SHORTLIST
            # =====================================
            print("🎯 Running shortlist logic...")
            status = "Shortlisted" if is_shortlisted(ai_result) else "Processed"

            print("🏷 Final Status:", status)

            # =====================================
            # SAVE MONGO
            # =====================================
            print("💾 Saving to MongoDB...")
            cv_collection.insert_one({
                "batch_id": batch_id,
                "file_name": file_name,
                "file_url": file_url,
                "raw_text": content,
                "ai_result": ai_result,
                "method": method,
                "status": status,
                "processed_at": time.time()
            })

            # =====================================
            # UPDATE MYSQL
            # =====================================
            print("🗄 Updating MySQL status...")
            db.execute(text("""
                UPDATE uploads
                SET status = :status
                WHERE id = :id
            """), {
                "status": status,
                "id": job_id
            })

            db.commit()

            print(f"🎉 DONE: {file_name} → {status}")

        except Exception as e:

            print("❌ ERROR OCCURRED:", str(e))

            db.execute(text("""
                UPDATE uploads
                SET status = 'Failed'
                WHERE id = :id
            """), {"id": job_id})

            db.commit()

        print("🔁 Waiting for next job...\n")
        time.sleep(1)


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    process_jobs()