from datetime import datetime
import re


def parse_date(date_str):
    if not date_str:
        return None

    date_str = str(date_str).strip().lower()

    if date_str in ["present", "current", "now", "to date"]:
        return datetime.today()

    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12"
    }

    # "Aug 2025"
    match = re.match(r"([a-z]+)\s*(\d{4})", date_str)
    if match:
        month = month_map.get(match.group(1)[:3])
        year = match.group(2)
        if month:
            return datetime.strptime(f"{year}-{month}", "%Y-%m")

    # "2025-08"
    try:
        return datetime.strptime(date_str, "%Y-%m")
    except:
        pass

    # "2025"
    try:
        return datetime.strptime(date_str, "%Y")
    except:
        return None


def calculate_experience(internships):
    """
    ONLY counts internships + jobs
    ignores projects completely
    """
    total_months = 0

    for job in internships or []:
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))

        if not start:
            continue

        if not end:
            end = datetime.today()

        diff_months = (end.year - start.year) * 12 + (end.month - start.month)
        total_months += max(diff_months, 0)

    return round(total_months / 12, 2)