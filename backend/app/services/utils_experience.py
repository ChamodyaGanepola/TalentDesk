from datetime import datetime
import re


def parse_date(date_str):
    if not date_str:
        return None

    date_str = str(date_str).strip().lower()

    if date_str in ["present", "current", "now", "to date", "ongoing"]:
        return datetime.today()

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


def calculate_experience(internships):
    """
    Counts only internships and jobs.
    Does not count projects, academic work, or hackathons.
    """
    total_months = 0

    for job in internships or []:
        if not isinstance(job, dict):
            continue

        job_type = str(job.get("type", "")).lower()

        if job_type and job_type not in ["internship", "job", "paid job", "work"]:
            continue

        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))

        if not start:
            continue

        if not end:
            end = datetime.today()

        diff_months = (end.year - start.year) * 12 + (end.month - start.month)

        if diff_months > 0:
            total_months += diff_months

    return round(total_months / 12, 2)