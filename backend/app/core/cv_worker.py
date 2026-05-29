import time
import asyncio
from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db_mongo import cv_collection

from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text
from app.services.evaluation import evaluate_candidate
import fitz  # PyMuPDF

# =========================
# CONFIG (YOU CAN CHANGE THIS)
# =========================
REQUIRED_SKILLS = {"python", "fastapi"}
REQUIRED_QUALS = {"bsc", "computer science"}
REQUIRED_EXP = 0


# =========================
# READ FILE
# =========================


def read_file(path: str) -> str:
    try:
        print("📄 Opening PDF:", path)

        doc = fitz.open(path)
        text = ""

        for page in doc:
            page_text = page.get_text("text")  # 🔥 IMPORTANT
            text += page_text + "\n"

        print("📄 Extracted text length:", len(text))

        return text.strip()

    except Exception as e:
        print("❌ PDF read error:", e)
        return ""

# =========================
# WORKER
# =========================
async def cv_worker_loop():

    print("🚀 CV Worker Started")

    while True:

        db = SessionLocal()

        try:

            job = db.execute(text("""
                SELECT id, batch_id, file_url, file_name
                FROM uploads
                WHERE status='Uploaded'
                ORDER BY id ASC
                LIMIT 1
            """)).fetchone()

            if not job:
                await asyncio.sleep(2)
                continue

            job_id, batch_id, file_url, file_name = job

            print(f"\n📥 Processing: {file_name}")

            db.execute(text("""
                UPDATE uploads SET status='Processing'
                WHERE id=:id
            """), {"id": job_id})
            db.commit()

            raw_text = read_file(file_url)

            print("📄 Text length:", len(raw_text))

            # =========================
            # OCR OR TEXT AI
            # =========================
            if len(raw_text) < 2000:
                print("🧠 Vision OCR used")
                extracted = vision_ocr(file_url)
                method = "vision_ocr"
            else:
                print("🧠 Text AI used")
                extracted = extract_cv_text(raw_text)
                method = "text_ai"

            # =========================
            # EVALUATION (IMPORTANT)
            # =========================
            is_selected = evaluate_candidate(
                extracted,
                REQUIRED_SKILLS,
                REQUIRED_QUALS,
                REQUIRED_EXP
            )

            status = "Shortlisted" if is_selected else "Rejected"

            print("🏷 Final Status:", status)

            # =========================
            # MONGO SAVE
            # =========================
            cv_collection.insert_one({
                "batch_id": batch_id,
                "file_name": file_name,
                "file_url": file_url,
                "raw_text": raw_text,
                "extracted": extracted,
                "method": method,
                "status": status,
                "processed_at": time.time()
            })

            # =========================
            # MYSQL UPDATE
            # =========================
            db.execute(text("""
                UPDATE uploads
                SET status=:status
                WHERE id=:id
            """), {
                "status": status,
                "id": job_id
            })

            db.commit()

            print(f"✅ DONE: {file_name}")

        except Exception as e:
            print("❌ Worker Error:", e)
            db.rollback()

        finally:
            db.close()

        await asyncio.sleep(1)