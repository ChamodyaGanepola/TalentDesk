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
    target_intern_label: str = "",
) -> int:
    """
    Canonical total experience in months.

    Uses the maximum of:
    1) months recomputed from job/internship date ranges
    2) stated experience_months / experience_years from extraction

    When internship include/exclude or an intern-role filter is active,
    prefer date-derived filtered months so the AI's unfiltered stated
    total cannot override the edited intern role.
    """
    data = data if isinstance(data, dict) else {}
    if internships is not None:
        jobs = coerce_work_entries(internships)
    else:
        jobs = coerce_work_entries(data)

    calculated = 0
    if jobs:
        calculated = calculate_experience_months(
            jobs,
            include_internships=include_internships,
            target_profession=target_profession,
            target_intern_label=target_intern_label,
        )

    stated = stated_experience_months(data)
    calculated = int(calculated or 0)
    stated = int(stated or 0)

    track = resolve_intern_label(target_profession, target_intern_label)
    internship_filter_active = (not include_internships) or (
        bool(track) and track.lower() != "intern"
    )

    has_paid_job = any(
        not is_internship_entry(job) for job in filter_jobs_and_internships(jobs)
    )

    # Filtered path: prefer date-derived months so AI stated totals cannot
    # override an internship include/exclude or intern-role filter.
    # If the model only returned internships but the CV stated multi-year
    # experience, fall back to stated months (jobs were likely missed).
    if internship_filter_active and jobs is not None:
        if has_paid_job or stated <= 0:
            return calculated
        return max(calculated, stated)

    return max(calculated, stated)


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
    "fulltime",
    "part-time",
    "part time",
    "parttime",
    "employment",
    "employee",
    "trainee",
    "apprenticeship",
    "apprentice",
    "contract",
    "contractor",
    "consultant",
    "permanent",
    "freelance",
    "freelancer",
    "self-employed",
    "self employed",
}

# Alternate keys models sometimes return instead of "internships"
_WORK_ENTRY_KEYS = (
    "work_experience",
    "workExperience",
    "jobs",
    "experiences",
    "employment",
    "professional_experience",
    "professionalExperience",
    "internships",
)

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


def _normalize_profession_name(profession: str) -> str:
    name = str(profession or "").strip().lower()
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    # Restore original casing via title-ish rebuild from cleaned tokens later;
    # callers that need display casing should use the cleaned display helper.
    return name


def _display_profession_name(profession: str) -> str:
    """Collapse whitespace/hyphens while keeping readable Title Case words."""
    cleaned = _normalize_profession_name(profession)
    if not cleaned:
        return ""
    # Prefer original spacing if already simple; otherwise title-case cleaned tokens.
    original = " ".join(str(profession or "").strip().replace("-", " ").replace("_", " ").split())
    if original.lower() == cleaned:
        return original
    return " ".join(w.capitalize() if w.lower() not in {"and", "of", "for"} else w.lower() for w in cleaned.split())


_LEVEL_PREFIXES = (
    "mid-level",
    "mid level",
    "entry-level",
    "entry level",
    "principal",
    "associate",
    "senior",
    "junior",
    "staff",
    "lead",
    "snr",
    "sr.",
    "jr.",
    "sr",
    "jr",
)

_LEAD_MANAGER_TITLES = {
    "team lead",
    "tech lead",
    "technical lead",
    "engineering lead",
    "engineering manager",
    "software manager",
    "development manager",
    "dev manager",
    "project lead",
    "manager",
}

_DEFAULT_INTERN_BASE = "Software Engineer"


def _is_lead_or_manager_title(lower: str) -> bool:
    if lower in _LEAD_MANAGER_TITLES:
        return True
    if lower.endswith(
        (" team lead", " tech lead", " technical lead", " engineering lead")
    ):
        return True
    if lower.endswith(" manager") and "engineer" not in lower and "developer" not in lower:
        return True
    return False


def intern_base_profession(profession: str) -> str:
    """
    Hiring position → IC base used for intern labels/matching.
    Senior Software Engineer → Software Engineer
    Team Lead → Software Engineer
    Software Engineer Intern → Software Engineer
    """
    lower = _normalize_profession_name(profession)
    if not lower:
        return ""

    for suffix in (" internship", " intern", " trainee"):
        if lower.endswith(suffix):
            lower = lower[: -len(suffix)].strip()
            break

    if not lower or lower in {"intern", "internship", "trainee"}:
        return _DEFAULT_INTERN_BASE

    if _is_lead_or_manager_title(lower):
        return _DEFAULT_INTERN_BASE

    # Strip level prefixes from the normalized form, then rebuild display.
    base_lower = lower
    while True:
        stripped = False
        for prefix in _LEVEL_PREFIXES:
            token = f"{prefix} "
            if base_lower.startswith(token):
                base_lower = base_lower[len(token) :].strip()
                stripped = True
                break
        if not stripped:
            break

    if not base_lower or _is_lead_or_manager_title(base_lower):
        return _DEFAULT_INTERN_BASE

    # Keep familiar casing for common SE base; otherwise title-case tokens.
    if base_lower == "software engineer":
        return _DEFAULT_INTERN_BASE
    return _display_profession_name(base_lower) or _DEFAULT_INTERN_BASE


def profession_intern_label(profession: str) -> str:
    """
    Hiring position → related intern title.
    Software Engineer → Software Engineer Intern
    Senior Software Engineer → Software Engineer Intern
    Team Lead → Software Engineer Intern
    Software Engineer Intern → Software Engineer Intern (no double Intern)
    """
    lower = _normalize_profession_name(profession)
    if not lower:
        return "Intern"

    if lower in {"intern", "internship", "trainee"}:
        return "Intern"

    base = intern_base_profession(profession)
    return f"{base} Intern" if base else "Intern"


def resolve_intern_label(profession: str = "", intern_label: str = "") -> str:
    """Prefer a user-edited intern label; otherwise derive from position."""
    custom = " ".join(str(intern_label or "").strip().split())
    if custom:
        return custom
    return profession_intern_label(profession)


def base_profession_for_intern_match(profession: str) -> str:
    """IC base role for matching internships to the hiring position."""
    return intern_base_profession(profession) or _display_profession_name(profession)


def internship_matches_profession(
    entry,
    profession: str,
    intern_label: str = "",
) -> bool:
    """
    Whether an internship relates to the target hiring position / intern label.
    Software Engineer → Software Engineer Intern
    Custom "QA Intern" → match QA internships
    """
    if not isinstance(entry, dict):
        return False
    if not is_internship_entry(entry):
        return False

    label = resolve_intern_label(profession, intern_label)
    if not label or label.lower() == "intern":
        # No specific track — count all internships when include is on.
        return True

    role = _normalize_type(entry.get("role") or entry.get("title"))
    company = _normalize_type(entry.get("company") or entry.get("organization"))
    blob = f"{role} {company}"
    base = intern_base_profession(label).lower()
    label_l = label.lower()

    # Match against IC base / intern title — not the senior/lead hiring title.
    if (base and base in blob) or (label_l and label_l in blob):
        return True

    # Prefer base tokens (without trailing "intern") so "Software Engineer Intern"
    # matches roles like "Software Engineer Intern" / "SE Intern".
    match_text = base or label_l
    tokens = [t for t in re.split(r"[^a-z0-9]+", match_text) if len(t) >= 2]
    skip = {
        "the",
        "and",
        "of",
        "for",
        "a",
        "an",
        "intern",
        "internship",
        "trainee",
        "senior",
        "junior",
        "lead",
        "team",
        "manager",
    }
    meaningful = [t for t in tokens if t not in skip]

    if meaningful and all(t in blob for t in meaningful):
        return True

    if len(meaningful) == 1 and meaningful[0] in blob.split():
        return True

    return False


def normalize_work_entry(entry) -> dict | None:
    """
    Normalize a work entry so type is job/internship when possible.
    Blank or synonym types with employer/dates become countable jobs.
    """
    if not isinstance(entry, dict):
        return None

    out = dict(entry)
    job_type = _normalize_type(out.get("type"))
    role = _normalize_type(out.get("role") or out.get("title"))
    company = _normalize_type(out.get("company") or out.get("organization"))
    blob = f"{role} {company}"

    # Map common synonyms onto allowed types
    if job_type in {
        "fulltime",
        "full-time",
        "full time",
        "parttime",
        "part-time",
        "part time",
        "permanent",
        "contract",
        "contractor",
        "consultant",
        "freelance",
        "freelancer",
        "self-employed",
        "self employed",
        "paid job",
        "work",
        "employment",
        "employee",
    }:
        out["type"] = "job"
        job_type = "job"
    elif job_type in INTERNSHIP_WORK_TYPES:
        out["type"] = "internship"
        job_type = "internship"

    if not job_type:
        if ("intern" in role and "internal" not in role) or any(
            t in role for t in ("trainee", "apprentice")
        ):
            out["type"] = "internship"
            job_type = "internship"
        elif company or out.get("start_date") or out.get("end_date"):
            projectish = any(
                t in blob
                for t in (
                    "personal project",
                    "academic project",
                    "university project",
                    "hackathon",
                    "capstone",
                    "coursework",
                    "assignment",
                )
            )
            if projectish and "project manager" not in blob:
                out["type"] = "project"
                job_type = "project"
            else:
                out["type"] = "job"
                job_type = "job"

    # Keep role/company keys consistent for downstream matching
    if not out.get("role") and out.get("title"):
        out["role"] = out.get("title")
    if not out.get("company") and out.get("organization"):
        out["company"] = out.get("organization")

    return out


def coerce_work_entries(data) -> list:
    """
    Collect work entries from work_experience / internships / common
    alternate keys. Prefer the longest non-empty list. Normalize types.
    """
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        candidates = [
            value
            for key in _WORK_ENTRY_KEYS
            if isinstance((value := data.get(key)), list) and value
        ]
        raw = max(candidates, key=len) if candidates else []
    else:
        raw = []

    normalized = []
    for entry in raw:
        item = normalize_work_entry(entry)
        if item is not None:
            normalized.append(item)
    return normalized


def is_job_or_internship(entry) -> bool:
    """
    Only real jobs and internships count toward experience.
    Projects, academic work, hackathons, etc. are excluded.
    """
    if not isinstance(entry, dict):
        return False

    entry = normalize_work_entry(entry) or entry
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
    if isinstance(entries, dict):
        entries = coerce_work_entries(entries)
    elif not isinstance(entries, list):
        return []
    else:
        entries = coerce_work_entries(entries)
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


def _entry_date_range(job) -> tuple[datetime, datetime] | None:
    """Parse a work entry into a (start, end) range, or None if unusable."""
    start = parse_date(job.get("start_date"))
    end = parse_date(job.get("end_date"))

    if not start:
        return None

    if not end:
        end = now_sri_lanka().replace(tzinfo=None)
    else:
        # Year-only end dates parse as Jan 1; treat as end of that year.
        end_raw = str(job.get("end_date") or "").strip()
        if re.fullmatch(r"\d{4}", end_raw):
            end = end.replace(month=12, day=31)

    if end < start:
        return None
    return start, end


def _months_between(start: datetime, end: datetime) -> int:
    """Month span matching prior inclusive-ish behavior (Jan→Jan ≈ 12)."""
    if start == end:
        return 1
    diff = (end.year - start.year) * 12 + (end.month - start.month)
    return max(diff, 1) if diff >= 0 else 0


def _merge_month_ranges(ranges: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union overlapping/adjacent date ranges so concurrent jobs are not double-counted."""
    if not ranges:
        return []

    ordered = sorted(ranges, key=lambda r: (r[0], r[1]))
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        # Adjacent months (end == next start) still merge for calendar continuity.
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def calculate_experience_months(
    internships,
    include_internships: bool = True,
    target_profession: str = "",
    target_intern_label: str = "",
) -> int:
    """
    Counts jobs always.
    Counts internships only when include_internships is True.
    When a profession/intern label is set, only related internships count.
    Multiple roles are all included; overlapping ranges are merged so
    calendar months are not double-counted.
    """
    profession = " ".join(str(target_profession or "").strip().split())
    intern_label = " ".join(str(target_intern_label or "").strip().split())
    track = resolve_intern_label(profession, intern_label)

    ranges: list[tuple[datetime, datetime]] = []
    for job in filter_jobs_and_internships(internships):
        if is_internship_entry(job):
            if not include_internships:
                continue
            if track and track.lower() != "intern":
                if not internship_matches_profession(
                    job, profession, intern_label=intern_label
                ):
                    continue

        span = _entry_date_range(job)
        if span:
            ranges.append(span)

    total_months = 0
    for start, end in _merge_month_ranges(ranges):
        total_months += _months_between(start, end)

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
