from openpyxl import Workbook
from openpyxl.styles import Font
from app.db_mongo import cv_collection
import os

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


def safe_join(values):
    if not values:
        return ""

    return ", ".join([str(v) for v in values if v])


def export_batch_shortlisted(batch_id: str):
    candidates = list(cv_collection.find({
        "batch_id": batch_id,
        "status": "Shortlisted"
    }))

    if not candidates:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Shortlisted"

    headers = [
        "No",
        "Name",
        "CV File",
        "Email Address",
        "Contact No",
        "Skills",
        "Total Work Experience",
        "Professional Qualifications"
    ]

    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for index, candidate in enumerate(candidates, start=1):
        exp = candidate.get("experience_years", 0)

        try:
            exp = float(exp)
        except Exception:
            exp = 0

        ws.append([
            index,
            candidate.get("name", ""),
            candidate.get("file_name", ""),
            candidate.get("email", ""),
            candidate.get("contact_no", ""),
            safe_join(candidate.get("skills", [])),
            exp,
            safe_join(candidate.get("qualifications", []))
        ])

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            value = str(cell.value or "")
            max_length = max(max_length, len(value))

        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    file_name = f"{batch_id}.xlsx"
    file_path = os.path.join(EXPORT_DIR, file_name)

    wb.save(file_path)

    return file_path