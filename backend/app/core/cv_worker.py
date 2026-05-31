import time
import asyncio
from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db_mongo import cv_collection

from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text
from app.services.evaluation import evaluate_candidate
import fitz  # PyMuPDF

from app.services.export_service import export_batch_shortlisted


# =========================
# BATCH COMPLETION CHECK
# =========================
def batch_completed(db, batch_id):

    remaining = db.execute(text("""
        SELECT COUNT(*)
        FROM uploads
        WHERE batch_id=:batch_id
        AND status IN ('Uploaded', 'Processing')
    """), {"batch_id": batch_id}).scalar()

    return remaining == 0


# =========================
# READ FILE
# =========================
def read_file(path: str) -> str:
    try:
        doc = fitz.open(path)
        text = ""

        for page in doc:
            text += page.get_text("text") + "\n"

        return text.strip()

    except Exception as e:
        print("❌ PDF read error:", e)
        return ""


# =========================
# LOAD REQUIREMENTS
# =========================
def load_batch_requirements(db, batch_id: str):

    skills = db.execute(text("""
        SELECT s.name
        FROM batch_skills bs
        JOIN skills s ON s.id = bs.skill_id
        WHERE bs.batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchall()

    quals = db.execute(text("""
        SELECT q.name
        FROM batch_qualifications bq
        JOIN qualifications q ON q.id = bq.qualification_id
        WHERE bq.batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchall()

    exp = db.execute(text("""
        SELECT experience_type, experience_value
        FROM upload_batches
        WHERE batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchone()

    return {
        "skills": [r[0] for r in skills],
        "qualifications": [r[0] for r in quals],
        "experience_type": exp[0] if exp else "minimum",
        "experience_value": exp[1] if exp else 0
    }


# =========================
# EXPERIENCE CHECK
# =========================
def check_experience(cv_exp, req_type, req_value):

    cv_exp = float(cv_exp or 0)
    req_value = float(req_value or 0)

    if req_type == "minimum":
        return cv_exp >= req_value

    if req_type == "more_than":
        return cv_exp > req_value

    if req_type == "exact":
        return abs(cv_exp - req_value) < 0.01

    return True


# =========================
# WORKER LOOP
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

            # =========================
            # MARK PROCESSING
            # =========================
            db.execute(text("""
                UPDATE uploads SET status='Processing'
                WHERE id=:id
            """), {"id": job_id})
            db.commit()

            # =========================
            # LOAD REQUIREMENTS
            # =========================
            req = load_batch_requirements(db, batch_id)

            required_skills = set(req["skills"])
            required_quals = set(req["qualifications"])
            required_exp = req["experience_value"]
            exp_type = req["experience_type"]

            # =========================
            # READ CV
            # =========================
            raw_text = read_file(file_url)

            if len(raw_text) < 2000:
                extracted = vision_ocr(file_url)
                method = "vision_ocr"
            else:
                extracted = extract_cv_text(raw_text)
                method = "text_ai"

            # =========================
            # EXPERIENCE
            # =========================
            cv_exp = float(extracted.get("experience_years") or 0)

            exp_ok = check_experience(cv_exp, exp_type, required_exp)

            # =========================
            # EVALUATION
            # =========================
            is_selected = evaluate_candidate(
                extracted,
                required_skills,
                required_quals,
                required_exp
            )

            final = is_selected and exp_ok

            status = "Shortlisted" if final else "Rejected"

            print("🏷 Final Status:", status)

            # =========================
            # SAVE TO MONGO (ENRICHED)
            # =========================
            cv_collection.insert_one({
                "batch_id": batch_id,

                "name": extracted.get("name"),
                "email": extracted.get("email"),
                "contact_no": extracted.get("contact_no"),

                "experience_years": extracted.get("experience_years"),
                "profession": extracted.get("profession"),

                "skills": extracted.get("skills", []),
                "qualifications": extracted.get("qualifications", []),

                "file_name": file_name,
                "file_url": file_url,

                "status": status,
                "method": method,

                "raw_text": raw_text,
                "extracted": extracted,

                "processed_at": time.time()
            })

            # =========================
            # UPDATE MYSQL
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

            # =========================
            # EXPORT ONLY ONCE PER BATCH
            # =========================
            if batch_completed(db, batch_id):

                existing = db.execute(text("""
                    SELECT id FROM batch_exports
                    WHERE batch_id=:batch_id
                """), {"batch_id": batch_id}).fetchone()

                if not existing:

                    excel_path = export_batch_shortlisted(batch_id)

                    if excel_path:

                        db.execute(text("""
                            INSERT INTO batch_exports
                            (
                                batch_id,
                                excel_file
                            )
                            VALUES
                            (
                                :batch_id,
                                :excel_file
                            )
                        """), {
                            "batch_id": batch_id,
                            "excel_file": excel_path
                        })

                        db.commit()

                        print(f"📊 Excel Generated: {excel_path}")

            print(f"✅ DONE: {file_name}")

        except Exception as e:
            print("❌ Worker Error:", e)
            db.rollback()

        finally:
            db.close()

        await asyncio.sleep(1)