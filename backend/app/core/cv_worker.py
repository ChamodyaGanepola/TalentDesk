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

import fitz
import re


# =========================
# HELPERS


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

    return {
        "skills": skills,
        "qualifications": qualifications,
        "experience_type": exp_row[0] if exp_row else "minimum",
        "experience_value": exp_row[1] if exp_row else 0
    }


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
            exp_type = req["experience_type"]
            required_exp = req["experience_value"]

            # =========================
            # READ CV
            # =========================
            raw_text = read_file(file_url)
            print("Raw text length:", len(raw_text))
            if len(raw_text) < 1500:
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
            # MATCHING (LINKEDIN-LEVEL)
            # =========================
            result = evaluate_candidate(
                cv={
                    "skills": cv_skills,
                    "qualifications": cv_quals,
                    "experience_years": cv_exp,
                },
                required_skills=required_skills,
                required_quals=required_quals,
                exp_type=exp_type,
                exp_value=required_exp
            )

            skills_match = result["skills_ok"]
            quals_match = result["qual_ok"]
            exp_match = result["exp_ok"]
            final = result["match"]

            status = "Shortlisted" if final else "Rejected"

            print("\n======================")
            print("RESULT")
            print("Skills:", skills_match)
            print("Qualifications:", quals_match)
            print("Experience:", exp_match)
            print("FINAL STATUS:", status)
            print("======================\n")

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
            if batch_completed(db, batch_id):

                print(f"Batch completed: {batch_id}")

                existing = db.execute(text("""
                    SELECT id FROM batch_exports
                    WHERE batch_id=:batch_id
                """), {"batch_id": batch_id}).fetchone()

                excel_path = None

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
                # FINAL EVENT (cv_proceed)
                # =========================
                await manager.broadcast({
                    "event": "cv_proceed",
                    "batch_id": batch_id,
                    "message": "All CVs processed successfully"
                })

                # optional extra events (kept your flow intact)
                await manager.broadcast({
                    "event": "batch_completed",
                    "batch_id": batch_id
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