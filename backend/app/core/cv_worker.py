import time
import asyncio
from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db_mongo import cv_collection
from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text
from app.services.matching_service import evaluate_candidate
from app.services.export_service import export_batch_shortlisted
from app.ws.manager import manager
from app.services.qualification_ai import normalize_and_match_qualifications
import fitz
import re


# =========================
# HELPERS
# =========================

def parse_experience(value):
    if not value:
        return 0
    try:
        return float(value)
    except:
        match = re.search(r"\d+(\.\d+)?", str(value))
        return float(match.group()) if match else 0


def batch_completed(db, batch_id):
    remaining = db.execute(text("""
        SELECT COUNT(*)
        FROM uploads
        WHERE batch_id=:batch_id
        AND status IN ('Uploaded', 'Processing')
    """), {"batch_id": batch_id}).scalar()

    return remaining == 0


def read_file(path: str) -> str:
    try:
        doc = fitz.open(path)
        text_data = ""
        for page in doc:
            text_data += page.get_text("text") + "\n"
        return text_data.strip()
    except Exception as e:
        print("PDF read error:", e)
        return ""


def load_batch_requirements(db, batch_id: str):
    skills_rows = db.execute(text("""
        SELECT s.name
        FROM batch_skills bs
        JOIN skills s ON s.id = bs.skill_id
        WHERE bs.batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchall()

    quals_rows = db.execute(text("""
        SELECT q.name
        FROM batch_qualifications bq
        JOIN qualifications q ON q.id = bq.qualification_id
        WHERE bq.batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchall()

    exp_row = db.execute(text("""
        SELECT experience_type, experience_value
        FROM upload_batches
        WHERE batch_id = :batch_id
    """), {"batch_id": batch_id}).fetchone()

    skills = [r[0] for r in skills_rows] if skills_rows else []
    qualifications = [r[0] for r in quals_rows] if quals_rows else []

    experience_type = exp_row[0] if exp_row else "minimum"
    experience_value = exp_row[1] if exp_row else 0

    return {
        "skills": skills,
        "qualifications": qualifications,
        "experience_type": experience_type,
        "experience_value": experience_value
    }


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


def evaluate_qualifications(cv_quals, required_quals):
    if not required_quals:
        return True

    cv_set = set([q.lower() for q in cv_quals or []])
    req_set = set([q.lower() for q in required_quals])

    return req_set.issubset(cv_set)


# =========================
# MAIN WORKER LOOP
# =========================

async def cv_worker_loop():
    print("CV Worker Started")

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

            print(f"\nProcessing: {file_name}")

            # mark processing
            db.execute(text("""
                UPDATE uploads SET status='Processing'
                WHERE id=:id
            """), {"id": job_id})
            db.commit()

            # =========================
            # LOAD REQUIREMENTS
            # =========================
            req = load_batch_requirements(db, batch_id)
            required_skills = req["skills"]
            required_quals = req["qualifications"]
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

            cv_exp = parse_experience(extracted.get("experience_years"))
            cv_skills = extracted.get("skills", [])
            cv_quals = extracted.get("qualifications", [])

            print("Extracted Experience:", cv_exp)
            print("Extracted Skills:", cv_skills)
            print("Extracted Qualifications:", cv_quals)

            # =========================
            # MATCHING
            # =========================
            skills_match = True if not required_skills else all(
                s.lower() in [cs.lower() for cs in cv_skills]
                for s in required_skills
            )

            # =========================
# QUALIFICATIONS MATCH (OpenAI)
# =========================
            quals_match_result = normalize_and_match_qualifications(cv_quals, required_quals)
            quals_match = quals_match_result.get("match", False)
            reason = quals_match_result.get("reason", "")
            print(f"Qualifications Match: {quals_match} | Reason: {reason}")
            exp_match = check_experience(cv_exp, exp_type, required_exp)
            print(f"Skills Match: {skills_match} | Qualifications Match: {quals_match} | Experience Match: {exp_match}")
            final = skills_match and quals_match and exp_match
            status = "Shortlisted" if final else "Rejected"

            print("🏷 Final Status:", status)

            # =========================
            # SAVE TO MONGO
            # =========================
            cv_collection.insert_one({
                "batch_id": batch_id,
                "name": extracted.get("name"),
                "email": extracted.get("email"),
                "skills": list(cv_skills),
                "qualifications": list(cv_quals),
                "experience_raw": extracted.get("experience_years"),
                "experience_years": cv_exp,
                "file_name": file_name,
                "file_url": file_url,
                "status": status,
                "method": method,
                "processed_at": time.time()
            })

            # =========================
            # UPDATE MYSQL
            # =========================
            db.execute(text("""
                UPDATE uploads
                SET status=:status
                WHERE id=:id
            """), {"status": status, "id": job_id})
            db.commit()

            # =========================
            # EXPORT EXCEL (ONCE PER BATCH)
            # =========================
            excel_path = None

            if batch_completed(db, batch_id):

                existing = db.execute(text("""
                    SELECT id FROM batch_exports
                    WHERE batch_id=:batch_id
                """), {"batch_id": batch_id}).fetchone()

                if not existing:
                    excel_path = export_batch_shortlisted(batch_id)

                    if excel_path:
                        db.execute(text("""
                            INSERT INTO batch_exports(batch_id, excel_file)
                            VALUES(:batch_id, :excel_file)
                        """), {
                            "batch_id": batch_id,
                            "excel_file": excel_path
                        })
                        db.commit()

                # =========================
                # CHECK FINAL RESULT
                # =========================
                shortlisted_count = db.execute(text("""
                    SELECT COUNT(*)
                    FROM uploads
                    WHERE batch_id=:batch_id
                    AND status='Shortlisted'
                """), {"batch_id": batch_id}).scalar()

                if shortlisted_count == 0:
                    await manager.broadcast({
                        "event": "batch_completed_no_results",
                        "batch_id": batch_id,
                        "message": "All CVs were rejected"
                    })
                else:
                    await manager.broadcast({
                        "event": "batch_completed",
                        "batch_id": batch_id,
                        "message": "Batch processing completed"
                    })

                if excel_path:
                    await manager.broadcast({
                        "event": "excel_exported",
                        "batch_id": batch_id,
                        "file": excel_path
                    })

        except Exception as e:
            print("Worker Error:", e)
            db.rollback()

        finally:
            db.close()

        await asyncio.sleep(1)