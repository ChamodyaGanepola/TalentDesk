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


def stated_experience_months(data: dict | None) -> int:
    """
    Best effort from AI/model numeric fields only.
    - Prefer positive experience_months
    - Also consider experience_years (e.g. years=5, months=0 → 60)
    """
    if not isinstance(data, dict):
        return 0

    candidates: list[int] = []

    raw_months = data.get("experience_months")
    if raw_months is not None:
        try:
            months = int(round(float(raw_months)))
            if months > 0:
                candidates.append(months)
        except Exception:
            pass

    raw_years = data.get("experience_years")
    if raw_years is not None:
        converted = years_to_months(raw_years)
        if converted > 0:
            candidates.append(converted)

    return max(candidates) if candidates else 0


def resolve_experience_months(
    data: dict | None = None,
    *,
    internships=None,
    include_internships: bool = True,
    target_profession: str = "",
) -> int:
    """
    Canonical total experience in months.

    Uses the maximum of:
    1) months recomputed from job/internship date ranges
    2) stated experience_months / experience_years from extraction

    This avoids undercounting when dates fail to parse but the model
    still reported years (e.g. experience_years=5, experience_months=0).
    """
    data = data if isinstance(data, dict) else {}
    jobs = internships if internships is not None else data.get("internships")

    calculated = 0
    if jobs:
        calculated = calculate_experience_months(
            jobs,
            include_internships=include_internships,
            target_profession=target_profession,
        )

    stated = stated_experience_months(data)
    return max(int(calculated or 0), int(stated or 0))


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

INTERNSHIP_WORK_TYPES = {
    "internship",
    "intern",
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


def is_internship_entry(entry) -> bool:
    """True when the work entry is an internship/trainee-style role."""
    if not isinstance(entry, dict):
        return False

    job_type = _normalize_type(entry.get("type"))
    if job_type in INTERNSHIP_WORK_TYPES:
        return True

    role = _normalize_type(entry.get("role") or entry.get("title"))
    return "intern" in role and "internal" not in role


def profession_intern_label(profession: str) -> str:
    """
    Hiring position → related intern title.
    Software Engineer → Software Engineer Intern
    Software Engineer Intern → Software Engineer Intern (same, no double Intern)
    """
    name = " ".join(str(profession or "").strip().split())
    if not name:
        return "Intern"
    lower = name.lower()
    if (
        lower.endswith(" intern")
        or lower.endswith(" internship")
        or lower in {"intern", "internship", "trainee"}
    ):
        return name
    return f"{name} Intern"


def base_profession_for_intern_match(profession: str) -> str:
    """Strip trailing Intern/Internship so SE Intern matches SE Intern roles."""
    name = " ".join(str(profession or "").strip().split())
    lower = name.lower()
    for suffix in (" internship", " intern", " trainee"):
        if lower.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name


def internship_matches_profession(entry, profession: str) -> bool:
    """
    Whether an internship relates to the target hiring position.
    Software Engineer → Software Engineer Intern
    Software Engineer Intern → same intern experience (not Intern Intern)
    """
    if not isinstance(entry, dict):
        return False
    if not is_internship_entry(entry):
        return False

    profession = " ".join(str(profession or "").strip().split())
    if not profession:
        return True

    role = _normalize_type(entry.get("role") or entry.get("title"))
    company = _normalize_type(entry.get("company") or entry.get("organization"))
    blob = f"{role} {company}"
    prof = profession.lower()
    base = base_profession_for_intern_match(profession).lower()

    if prof in blob or (base and base in blob):
        return True

    # Prefer base tokens (without trailing "intern") so "Software Engineer Intern"
    # matches roles like "Software Engineer Intern" / "SE Intern".
    match_text = base or prof
    tokens = [t for t in re.split(r"[^a-z0-9]+", match_text) if len(t) >= 2]
    skip = {"the", "and", "of", "for", "a", "an", "intern", "internship", "trainee"}
    meaningful = [t for t in tokens if t not in skip]

    if meaningful and all(t in blob for t in meaningful):
        return True

    if len(meaningful) == 1 and meaningful[0] in blob.split():
        return True

    return False


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


def parse_include_internships(value) -> bool:
    """
    Batch/UI flag: whether internship months count toward experience.
    Default True for backward compatibility.
    """
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"0", "false", "no", "n", "exclude", "excluded", "off"}:
        return False
    if text in {"1", "true", "yes", "y", "include", "included", "on"}:
        return True
    return True


def calculate_experience_months(
    internships,
    include_internships: bool = True,
    target_profession: str = "",
) -> int:
    """
    Counts jobs always.
    Counts internships only when include_internships is True.
    When target_profession is set, only profession-related internships count
    (e.g. Software Engineer → Software Engineer Intern).
    """
    total_months = 0
    profession = " ".join(str(target_profession or "").strip().split())

    for job in filter_jobs_and_internships(internships):
        if is_internship_entry(job):
            if not include_internships:
                continue
            if profession and not internship_matches_profession(job, profession):
                continue

        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))

        if not start:
            continue

        if not end:
            end = now_sri_lanka().replace(tzinfo=None)
        else:
            # Year-only end dates parse as Jan 1; treat as end of that year.
            end_raw = str(job.get("end_date") or "").strip()
            if re.fullmatch(r"\d{4}", end_raw):
                end = end.replace(month=12, day=31)

        diff_months = (end.year - start.year) * 12 + (end.month - start.month)
        # Inclusive-ish month span: Jan 2020 → Jan 2021 ≈ 12 months.
        if diff_months >= 0:
            total_months += max(diff_months, 1) if start != end else 1
        # keep previous behavior for inverted ranges: skip
        elif diff_months < 0:
            continue

    return int(total_months)


def calculate_experience(
    internships,
    include_internships: bool = True,
    target_profession: str = "",
):
    """
    Backward-compatible helper that returns years as a float.
    Prefer calculate_experience_months() for storage.
    """
    return round(
        calculate_experience_months(
            internships,
            include_internships=include_internships,
            target_profession=target_profession,
        )
        / 12,
        2,
    )
