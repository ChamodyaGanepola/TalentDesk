import time
import asyncio
import traceback
import os
import fitz

from sqlalchemy import text

from app.db_mysql import SessionLocal
from app.db_mongo import cv_collection
from app.services.vision_ocr import vision_ocr
from app.services.ai_service import extract_cv_text
from app.services.matching_service import evaluate_candidate
from app.services.export_service import export_batch_shortlisted
from app.services.utils_experience import (
    months_to_label,
    months_to_years_float,
    parse_include_internships,
    resolve_experience_months,
    years_to_months,
)
from app.ws.manager import manager
from app.ws.broadcaster import broadcast_stats


# =========================
# HELPERS
# =========================
def parse_experience_months(
    extracted,
    *,
    include_internships: bool = True,
    target_profession: str = "",
) -> int:
    """Resolve CV experience to months (job dates + stated years/months)."""
    if not isinstance(extracted, dict):
        return years_to_months(extracted)

    return resolve_experience_months(
        extracted,
        internships=extracted.get("internships"),
        include_internships=include_internships,
        target_profession=target_profession,
    )


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

    try:
        exp_row = db.execute(text("""
            SELECT experience_type, experience_value, include_internships, profession
            FROM upload_batches
            WHERE batch_id = :batch_id
        """), {
            "batch_id": batch_id
        }).fetchone()
        include_internships = parse_include_internships(
            exp_row[2] if exp_row and len(exp_row) > 2 else True
        )
        batch_profession = str(exp_row[3] or "").strip() if exp_row and len(exp_row) > 3 else ""
    except Exception:
        try:
            exp_row = db.execute(text("""
                SELECT experience_type, experience_value, include_internships
                FROM upload_batches
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id
            }).fetchone()
            include_internships = parse_include_internships(
                exp_row[2] if exp_row and len(exp_row) > 2 else True
            )
        except Exception:
            exp_row = db.execute(text("""
                SELECT experience_type, experience_value
                FROM upload_batches
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id
            }).fetchone()
            include_internships = True
        batch_profession = ""

    skills = [r[0] for r in skills_rows] if skills_rows else []
    qualifications = [r[0] for r in quals_rows] if quals_rows else []

    return {
        "skills": skills,
        "qualifications": qualifications,
        "experience_type": exp_row[0] if exp_row else "minimum",
        "experience_value": exp_row[1] if exp_row else 0,
        "include_internships": include_internships,
        "profession": batch_profession,
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

    shortlisted_count = int(counts["shortlisted_count"] or 0)
    rejected_count = int(counts["rejected_count"] or 0)
    failed_count = int(counts["failed_count"] or 0)
    total_count = int(counts["total_count"] or 0)

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
    excel_generated_at = None

    if shortlisted_count > 0:
        print(
            f"Generating Excel for batch {batch_id}: "
            f"{shortlisted_count} shortlisted / {total_count} total"
        )

        batch_profession = ""
        try:
            row = db.execute(text("""
                SELECT profession
                FROM upload_batches
                WHERE batch_id = :batch_id
                LIMIT 1
            """), {"batch_id": batch_id}).mappings().first()
            batch_profession = " ".join(
                str((row or {}).get("profession") or "").strip().split()
            )
            print(f"Batch profession for Excel: '{batch_profession or '(none)'}'")
        except Exception as e:
            print("Could not load batch profession for export:", e)

        try:
            export_result = export_batch_shortlisted(
                batch_id,
                total_cvs=total_count,
                db=db,
                position=batch_profession or None,
            )
        except Exception as export_error:
            print("Excel export error:", export_error)
            traceback.print_exc()
            export_result = None

            # One retry after a short wait (Mongo write lag).
            try:
                await asyncio.sleep(1)
                export_result = export_batch_shortlisted(
                    batch_id,
                    total_cvs=total_count,
                    db=db,
                    position=batch_profession,
                )
            except Exception as retry_error:
                print("Excel export retry failed:", retry_error)
                traceback.print_exc()
                export_result = None

        if export_result:
            excel_path = export_result["file_path"]
            excel_generated_at = export_result.get("generated_at")

            if existing:
                db.execute(text("""
                    UPDATE batch_exports
                    SET excel_file=:excel_file, created_at=:created_at
                    WHERE id=:id
                """), {
                    "excel_file": excel_path,
                    "created_at": excel_generated_at,
                    "id": existing[0],
                })
            else:
                db.execute(text("""
                    INSERT INTO batch_exports(batch_id, excel_file, created_at)
                    VALUES(:batch_id, :excel_file, :created_at)
                """), {
                    "batch_id": batch_id,
                    "excel_file": excel_path,
                    "created_at": excel_generated_at,
                })
            db.commit()
            print(f"Excel saved for batch {batch_id}: {excel_path}")
        elif existing:
            excel_path = existing[1]
            print(
                f"Excel export returned empty for batch {batch_id}; "
                f"keeping previous file {excel_path}"
            )
        else:
            print(
                f"ERROR: {shortlisted_count} shortlisted CV(s) but "
                f"Excel was not generated for batch {batch_id}"
            )

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
            "total": total_count,
            "shortlisted": shortlisted_count,
            "rejected": rejected_count,
            "failed": failed_count,
            "message": "Excel file generated successfully"
        })
    elif shortlisted_count == 0:
        await manager.broadcast({
            "event": "batch_completed_no_results",
            "batch_id": batch_id,
            "total": total_count,
            "shortlisted": shortlisted_count,
            "rejected": rejected_count,
            "failed": failed_count,
            "message": "All CVs were processed, but no candidates were shortlisted. No Excel file was generated."
        })
    else:
        # Shortlisted exists but export failed/empty — still signal completion
        # so 1-CV and multi-CV flows can finish and redirect.
        await manager.broadcast({
            "event": "excel_exported",
            "batch_id": batch_id,
            "file": None,
            "total": total_count,
            "shortlisted": shortlisted_count,
            "rejected": rejected_count,
            "failed": failed_count,
            "message": "Batch completed with shortlisted candidates"
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
                await asyncio.sleep(float(os.getenv("CV_WORKER_POLL_SEC", "2")))
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
            include_internships = req.get("include_internships", True)
            batch_profession = (req.get("profession") or "").strip()

            raw_text = read_file(file_url)

            print("Raw text length:", len(raw_text))
            print("Include internships:", include_internships)
            print("Batch profession:", batch_profession or "(none)")

            if len(raw_text.strip()) < 300:
                extracted = vision_ocr(
                    file_url,
                    include_internships=include_internships,
                    target_profession=batch_profession,
                )
                method = "vision_ocr"
            else:
                extracted = extract_cv_text(
                    raw_text,
                    include_internships=include_internships,
                    target_profession=batch_profession,
                )
                method = "text_ai"

            cv_exp_months = parse_experience_months(
                extracted,
                include_internships=include_internships,
                target_profession=batch_profession,
            )
            cv_skills = extracted.get("skills", []) or []
            cv_quals = extracted.get("qualifications", []) or []

            print("Extracted Experience (months):", cv_exp_months)
            print("Extracted Experience (label):", months_to_label(cv_exp_months))
            print("Extracted Skills:", cv_skills)
            print("Extracted Qualifications:", cv_quals)

            result = evaluate_candidate(
                cv={
                    "skills": cv_skills,
                    "qualifications": cv_quals,
                    "experience_months": cv_exp_months,
                    "experience_years": months_to_years_float(cv_exp_months),
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
                "experience_months": cv_exp_months,
                "experience_years": months_to_years_float(cv_exp_months),
                "experience_label": months_to_label(cv_exp_months),
                "profession": extracted.get("profession"),
                "batch_profession": batch_profession,
                "internships": extracted.get("internships", []),
                "include_internships": include_internships,
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

        await asyncio.sleep(float(os.getenv("CV_WORKER_POLL_SEC", "2")))