from openpyxl import Workbook
from app.db_mongo import cv_collection
import os

EXPORT_DIR = "exports"

os.makedirs(EXPORT_DIR, exist_ok=True)


def export_batch_shortlisted(batch_id):

    candidates = list(
        cv_collection.find({
            "batch_id": batch_id,
            "status": "Shortlisted"
        })
    )

    if not candidates:
        return None

    wb = Workbook()

    ws = wb.active

    ws.title = "Shortlisted"

    ws.append([
        "No",
        "Name",
        "CV File",
        "Email Address",
        "Contact No",
        "SKills",
        "Total Work Experience",
        "Professional Qualifications"
    ])

    for index, candidate in enumerate(
        candidates,
        start=1
    ):

        ws.append([
            index,
            candidate.get("name", ""),
            candidate.get("file_name", ""),
            candidate.get("email", ""),
            candidate.get("contact_no", ""),
             ", ".join(candidate.get("skills", [])),
            candidate.get("experience_years", 0),
            ", ".join(
                candidate.get(
                    "qualifications",
                    []
                )
            )
        ])

    file_name = f"{batch_id}.xlsx"

    file_path = os.path.join(
        EXPORT_DIR,
        file_name
    )

    wb.save(file_path)

    return file_path