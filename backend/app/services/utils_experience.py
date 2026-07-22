from datetime import datetime
from app.services.timezone_sl import now_sri_lanka
import re


def parse_date(date_str):
    if not date_str:
        return None

    date_str = str(date_str).strip().lower()

    if date_str in ["present", "current", "now", "to date", "ongoing"]:
        return now_sri_lanka().replace(tzinfo=None)

    month_map = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "sept": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }

    # Remove commas
    date_str = date_str.replace(",", " ")

    # Example: Aug 2025 / August 2025
    match = re.match(r"([a-z]+)\s+(\d{4})", date_str)
    if match:
        month = month_map.get(match.group(1))
        year = match.group(2)

        if month:
            return datetime.strptime(f"{year}-{month}", "%Y-%m")

    # Example: 2025-08-01
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        pass

    # Example: 2025-08
    try:
        return datetime.strptime(date_str, "%Y-%m")
    except Exception:
        pass

    # Example: 2025
    try:
        return datetime.strptime(date_str, "%Y")
    except Exception:
        pass

    return None


def years_to_months(years) -> int:
    try:
        value = float(years or 0)
    except Exception:
        match = re.search(r"\d+(\.\d+)?", str(years))
        value = float(match.group()) if match else 0.0

    if value < 0:
        return 0

    return int(round(value * 12))


def months_to_label(total_months) -> str:
    try:
        months = int(total_months or 0)
    except Exception:
        months = 0

    if months < 0:
        months = 0

    years = months // 12
    rem = months % 12

    y_label = "1 year" if years == 1 else f"{years} years"
    m_label = "1 month" if rem == 1 else f"{rem} months"

    if years == 0 and rem == 0:
        return "0 months"
    if years == 0:
        return m_label
    if rem == 0:
        return y_label
    return f"{y_label} {m_label}"


def months_to_years_float(total_months) -> float:
    try:
        months = int(total_months or 0)
    except Exception:
        months = 0

    if months < 0:
        months = 0

    return round(months / 12, 2)


def normalize_requirement_months(value) -> int:
    """
    upload_batches.experience_value is stored in months.
    Accepts ints/floats safely.
    """
    try:
        return max(int(round(float(value or 0))), 0)
    except Exception:
        return 0


ALLOWED_WORK_TYPES = {
    "internship",
    "intern",
    "job",
    "paid job",
    "work",
    "full-time",
    "full time",
    "part-time",
    "part time",
    "employment",
    "employee",
    "trainee",
    "apprenticeship",
    "apprentice",
}

EXCLUDED_WORK_TYPES = {
    "project",
    "projects",
    "personal project",
    "academic",
    "academic project",
    "university project",
    "assignment",
    "hackathon",
    "coursework",
    "course",
    "volunteer",
    "volunteering",
    "research project",
    "capstone",
    "freelance project",
}


def _normalize_type(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def is_job_or_internship(entry) -> bool:
    """
    Only real jobs and internships count toward experience.
    Projects, academic work, hackathons, etc. are excluded.
    """
    if not isinstance(entry, dict):
        return False

    job_type = _normalize_type(entry.get("type"))
    role = _normalize_type(entry.get("role") or entry.get("title"))
    company = _normalize_type(entry.get("company") or entry.get("organization"))
    blob = f"{job_type} {role} {company}"

    # Explicit exclusions first
    if job_type in EXCLUDED_WORK_TYPES:
        return False

    if any(
        token in blob
        for token in (
            "project",
            "hackathon",
            "assignment",
            "coursework",
            "capstone",
            "personal project",
        )
    ):
        # Still allow if clearly labeled as a job/internship type
        # and "project" only appears in a descriptive role (e.g. "Project Manager").
        if job_type not in ALLOWED_WORK_TYPES:
            return False
        if "project manager" not in blob and job_type in {"project", "projects"}:
            return False
        if job_type in EXCLUDED_WORK_TYPES or job_type.endswith("project"):
            return False

    if job_type in ALLOWED_WORK_TYPES:
        return True

    # No reliable type → do not count (prevents projects with blank type)
    return False


def filter_jobs_and_internships(entries) -> list:
    """Return only internship/job entries suitable for experience calculation."""
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if is_job_or_internship(entry)]


def calculate_experience_months(internships) -> int:
    """
    Counts only internships and jobs.
    Projects and other non-work items are ignored.
    Returns total experience in whole months.
    """
    total_months = 0

    for job in filter_jobs_and_internships(internships):
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))

        if not start:
            continue

        if not end:
            end = now_sri_lanka().replace(tzinfo=None)

        diff_months = (end.year - start.year) * 12 + (end.month - start.month)

        if diff_months > 0:
            total_months += diff_months

    return int(total_months)


def calculate_experience(internships):
    """
    Backward-compatible helper that returns years as a float.
    Prefer calculate_experience_months() for storage.
    """
    return round(calculate_experience_months(internships) / 12, 2)
