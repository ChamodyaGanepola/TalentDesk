import time
import asyncio
import traceback
import fitz
import re

from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db_mongo import cv_collection
from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text
from app.services.matching_service import evaluate_candidate
from app.services.export_service import export_batch_shortlisted
from app.ws.manager import manager
from app.ws.broadcaster import broadcast_stats


# =========================
# HELPERS
# =========================
def parse_experience(value):
    if not value:
        return 0.0

    try:
        return float(value)
    except Exception:
        match = re.search(r"\d+(\.\d+)?", str(value))
        return float(match.group()) if match else 0.0


def batch_completed(db, batch_id):
    remaining = db.execute(text("""
        SELECT COUNT(*)
        FROM uploads
        WHERE batch_id=:batch_id
        AND status IN ('Uploaded', 'Processing')
    """), {
        "batch_id": batch_id
    }).scalar()

    return remaining == 0


def read_file(path: str) -> str:
    try:
        doc = fitz.open(path)
        text_data = ""

        for page in doc:
            text_data += page.get_text("text") + "\n"

        doc.close()
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
    """), {
        "batch_id": batch_id
    }).fetchall()

    quals_rows = db.execute(text("""
        SELECT q.name
        FROM batch_qualifications bq
        JOIN qualifications q ON q.id = bq.qualification_id
        WHERE bq.batch_id = :batch_id
    """), {
        "batch_id": batch_id
    }).fetchall()

    exp_row = db.execute(text("""
        SELECT experience_type, experience_value
        FROM upload_batches
        WHERE batch_id = :batch_id
    """), {
        "batch_id": batch_id
    }).fetchone()

    skills = [r[0] for r in skills_rows] if skills_rows else []
    qualifications = [r[0] for r in quals_rows] if quals_rows else []

    return {
        "skills": skills,
        "qualifications": qualifications,
        "experience_type": exp_row[0] if exp_row else "minimum",
        "experience_value": exp_row[1] if exp_row else 0
    }


def mark_failed(db, job_id, error_message=None):
    db.execute(text("""
        UPDATE uploads
        SET status='Failed'
        WHERE id=:id
    """), {
        "id": job_id
    })
    db.commit()

    if error_message:
        print("Marked Failed:", error_message)


async def handle_batch_completion(db, batch_id):
    if not batch_completed(db, batch_id):
        return

    print(f"Batch completed: {batch_id}")

    counts = db.execute(text("""
        SELECT
            SUM(CASE WHEN status='Shortlisted' THEN 1 ELSE 0 END) AS shortlisted_count,
            SUM(CASE WHEN status='Rejected' THEN 1 ELSE 0 END) AS rejected_count,
            SUM(CASE WHEN status='Failed' THEN 1 ELSE 0 END) AS failed_count,
            COUNT(*) AS total_count
        FROM uploads
        WHERE batch_id=:batch_id
    """), {
        "batch_id": batch_id
    }).mappings().first()

    shortlisted_count = counts["shortlisted_count"] or 0
    rejected_count = counts["rejected_count"] or 0
    failed_count = counts["failed_count"] or 0
    total_count = counts["total_count"] or 0

    existing = db.execute(text("""
        SELECT id, excel_file
        FROM batch_exports
        WHERE batch_id=:batch_id
        ORDER BY id DESC
        LIMIT 1
    """), {
        "batch_id": batch_id
    }).fetchone()

    excel_path = None

    if shortlisted_count > 0:
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
        else:
            excel_path = existing[1]

    await manager.broadcast({
        "event": "cv_proceed",
        "batch_id": batch_id,
        "message": "All CVs processed successfully",
        "total": total_count,
        "shortlisted": shortlisted_count,
        "rejected": rejected_count,
        "failed": failed_count
    })

    await manager.broadcast({
        "event": "batch_completed",
        "batch_id": batch_id,
        "total": total_count,
        "shortlisted": shortlisted_count,
        "rejected": rejected_count,
        "failed": failed_count
    })

    if excel_path:
        await manager.broadcast({
            "event": "excel_exported",
            "batch_id": batch_id,
            "file": excel_path,
            "message": "Excel file generated successfully"
        })
    else:
        await manager.broadcast({
            "event": "batch_completed_no_results",
            "batch_id": batch_id,
            "total": total_count,
            "shortlisted": shortlisted_count,
            "rejected": rejected_count,
            "failed": failed_count,
            "message": "All CVs were processed, but no candidates were shortlisted. No Excel file was generated."
        })


# =========================
# MAIN WORKER LOOP
# =========================
async def cv_worker_loop():
    print("CV Worker Started")

    while True:
        db = SessionLocal()
        job_id = None
        batch_id = None

        try:
            job = db.execute(text("""
                SELECT id, batch_id, file_url, file_name
                FROM uploads
                WHERE status='Uploaded'
                ORDER BY id ASC
                LIMIT 1
            """)).fetchone()

            if not job:
                db.close()
                await asyncio.sleep(2)
                continue

            job_id, batch_id, file_url, file_name = job

            claim_result = db.execute(text("""
                UPDATE uploads
                SET status='Processing'
                WHERE id=:id
                AND status='Uploaded'
            """), {
                "id": job_id
            })

            db.commit()

            if claim_result.rowcount == 0:
                db.close()
                await asyncio.sleep(1)
                continue

            await broadcast_stats()

            print(f"\nProcessing: {file_name}")

            req = load_batch_requirements(db, batch_id)

            required_skills = req["skills"]
            required_quals = req["qualifications"]
            exp_type = req["experience_type"]
            required_exp = req["experience_value"]

            raw_text = read_file(file_url)

            print("Raw text length:", len(raw_text))

            if len(raw_text.strip()) < 300:
                extracted = vision_ocr(file_url)
                method = "vision_ocr"
            else:
                extracted = extract_cv_text(raw_text)
                method = "text_ai"

            cv_exp = parse_experience(extracted.get("experience_years"))
            cv_skills = extracted.get("skills", []) or []
            cv_quals = extracted.get("qualifications", []) or []

            print("Extracted Experience:", cv_exp)
            print("Extracted Skills:", cv_skills)
            print("Extracted Qualifications:", cv_quals)

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

            status = "Shortlisted" if result["match"] else "Rejected"

            print("\n======================")
            print("RESULT")
            print("Skills:", result["skills_ok"])
            print("Qualifications:", result["qual_ok"])
            print("Experience:", result["exp_ok"])
            print("Score:", result.get("score"))
            print("FINAL STATUS:", status)
            print("======================\n")

            mongo_payload = {
                "upload_id": job_id,
                "batch_id": batch_id,
                "name": extracted.get("name"),
                "email": extracted.get("email"),
                "contact_no": extracted.get("contact_no"),
                "skills": list(cv_skills),
                "qualifications": list(cv_quals),
                "experience_raw": extracted.get("experience_years"),
                "experience_years": cv_exp,
                "profession": extracted.get("profession"),
                "internships": extracted.get("internships", []),
                "file_name": file_name,
                "file_url": file_url,
                "status": status,
                "method": method,
                "match_result": result,
                "processed_at": time.time()
            }

            cv_collection.update_one(
                {"upload_id": job_id},
                {"$set": mongo_payload},
                upsert=True
            )

            db.execute(text("""
                UPDATE uploads
                SET status=:status
                WHERE id=:id
                AND status='Processing'
            """), {
                "status": status,
                "id": job_id
            })

            db.commit()

            await broadcast_stats()

            await handle_batch_completion(db, batch_id)

        except Exception as e:
            print("Worker Error:", e)
            traceback.print_exc()
            db.rollback()

            # Only fail jobs that are still mid-processing. Do not overwrite
            # an already-committed Shortlisted/Rejected status.
            if job_id:
                try:
                    still_open = db.execute(text("""
                        SELECT status FROM uploads WHERE id=:id
                    """), {"id": job_id}).scalar()

                    if still_open in ("Uploaded", "Processing"):
                        mark_failed(db, job_id, str(e))
                        await broadcast_stats()
                except Exception as failed_error:
                    print("Could not mark job as failed:", failed_error)

        finally:
            db.close()

        await asyncio.sleep(1)