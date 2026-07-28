from app.services.vector_service import get_embedding, cosine_similarity
from app.services.qualification_ai import normalize_and_match_qualifications
from app.services.skill_ai import normalize_and_match_skills
from app.services.utils_experience import resolve_experience_months
from sqlalchemy import text
from app.db_mysql import SessionLocal

# =========================
# SKILL ONTOLOGY CACHE
# (fallback only if OpenAI skill matching fails)
# =========================
SKILL_ALIAS_MAP = {}
CANONICAL_SKILLS = set()
ALIASES_LOADED = False


COMMON_SKILL_ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "java script": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "react": "react",
    "next": "next.js",
    "nextjs": "next.js",
    "next.js": "next.js",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "vue.js": "vue.js",
    "angularjs": "angular",
    "angular.js": "angular",
    "angular": "angular",
    "expressjs": "express",
    "express.js": "express",
    "express": "express",
    "csharp": "c#",
    "c sharp": "c#",
    "c-sharp": "c#",
    "c#": "c#",
    "dotnet": ".net",
    ".net core": ".net",
    "asp.net": ".net",
    "asp.net core": ".net",
    ".net": ".net",
    "postgres": "postgresql",
    "postgre sql": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
    "mongo db": "mongodb",
    "mongodb": "mongodb",
    "mssql": "sql server",
    "microsoft sql server": "sql server",
    "sql server": "sql server",
    "html5": "html",
    "html": "html",
    "css3": "css",
    "css": "css",
    "amazon web services": "aws",
    "aws": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "gcp": "gcp",
    "microsoft azure": "azure",
    "azure": "azure",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "cicd": "ci/cd",
    "ci/cd": "ci/cd",
}


def load_skill_aliases():
    global SKILL_ALIAS_MAP, CANONICAL_SKILLS, ALIASES_LOADED

    db = SessionLocal()

    try:
        rows = db.execute(text("""
            SELECT canonical, alias FROM skill_aliases
        """)).fetchall()

        alias_map = dict(COMMON_SKILL_ALIASES)
        canonical_set = set(COMMON_SKILL_ALIASES.values())

        for canonical, alias in rows:
            canonical = str(canonical or "").lower().strip()
            alias = str(alias or "").lower().strip()

            if not canonical or not alias:
                continue

            canonical_set.add(canonical)
            alias_map[alias] = canonical
            alias_map[canonical] = canonical

        SKILL_ALIAS_MAP = alias_map
        CANONICAL_SKILLS = canonical_set
        ALIASES_LOADED = True

    except Exception as e:
        print("Skill alias load error:", e)
        SKILL_ALIAS_MAP = dict(COMMON_SKILL_ALIASES)
        CANONICAL_SKILLS = set(COMMON_SKILL_ALIASES.values())
        ALIASES_LOADED = True

    finally:
        db.close()


def ensure_aliases_loaded():
    if not ALIASES_LOADED:
        load_skill_aliases()


def clean_list(data):
    if not data:
        return []

    cleaned = []

    for item in data:
        if not item:
            continue

        value = str(item).strip().lower()

        if value and value not in cleaned:
            cleaned.append(value)

    return cleaned


def normalize_skill(skill: str) -> str:
    """Fallback-only synonym normalization."""
    ensure_aliases_loaded()

    value = str(skill or "").lower().strip()

    if not value:
        return ""

    compact = (
        value.replace(".", " ")
        .replace("_", " ")
        .replace("-", " ")
    )
    compact = " ".join(compact.split())

    if value in SKILL_ALIAS_MAP:
        return SKILL_ALIAS_MAP[value]

    if compact in SKILL_ALIAS_MAP:
        return SKILL_ALIAS_MAP[compact]

    no_space = compact.replace(" ", "")
    if no_space in SKILL_ALIAS_MAP:
        return SKILL_ALIAS_MAP[no_space]

    return value


# =========================
# FALLBACK SKILL MATCH
# Used ONLY when OpenAI is unavailable.
# Strict: known aliases + exact canonical equality.
# No embeddings / substring (those false-match java↔javascript, aws↔azure, etc.).
# =========================
def _missing_skills_fallback(cv_skills, required_skills) -> list[str]:
    """Required skills not covered by exact/alias canonical match."""
    cv_canonical = {
        normalize_skill(skill)
        for skill in cv_skills
        if skill and str(skill).strip()
    }
    cv_canonical = {s for s in cv_canonical if s}
    cv_exact = {str(s).strip().lower() for s in cv_skills if s and str(s).strip()}

    missing: list[str] = []
    for skill in required_skills:
        raw = str(skill or "").strip()
        if not raw:
            continue
        canon = normalize_skill(raw)
        if canon in cv_canonical or raw.lower() in cv_exact:
            continue
        missing.append(raw)
    return missing


def skill_match_fallback(cv_skills, required_skills):
    return len(_missing_skills_fallback(cv_skills, required_skills)) == 0


def skill_match_details(cv_skills, required_skills) -> dict:
    """
    Primary: OpenAI technology-identity matching (handles unknown aliases).
    Fallback: small known-alias map + exact match only if OpenAI fails.

    Returns {"match": bool, "missing": [required skills not found on CV]}.
    """
    required_skills = clean_list(required_skills)
    cv_skills = clean_list(cv_skills)

    if not required_skills:
        return {"match": True, "missing": []}

    if not cv_skills:
        return {"match": False, "missing": list(required_skills)}

    # Fast path: exact string coverage.
    required_set = set(required_skills)
    cv_set = set(cv_skills)
    if required_set.issubset(cv_set):
        return {"match": True, "missing": []}

    # Fast path: known-alias canonical coverage (safe local synonyms only).
    cv_canonical = {normalize_skill(s) for s in cv_skills if s}
    req_canonical = [normalize_skill(s) for s in required_skills if s]
    if req_canonical and all(r in cv_canonical for r in req_canonical):
        return {"match": True, "missing": []}

    ai_result = normalize_and_match_skills(cv_skills, required_skills)

    if isinstance(ai_result, dict) and not ai_result.get("openai_failed"):
        missing = [
            str(m).strip()
            for m in (ai_result.get("missing") or [])
            if str(m).strip()
        ]
        is_match = bool(ai_result.get("match", False)) and len(missing) == 0
        print(
            "OpenAI skill match:",
            is_match,
            ai_result.get("reason"),
            "missing=",
            missing,
        )
        return {"match": is_match, "missing": [] if is_match else missing}

    print(
        "OpenAI skill match failed; using strict alias fallback:",
        ai_result.get("reason") if isinstance(ai_result, dict) else ai_result,
    )
    missing = _missing_skills_fallback(cv_skills, required_skills)
    return {"match": len(missing) == 0, "missing": missing}


def skill_match(cv_skills, required_skills):
    """
    Primary: OpenAI technology-identity matching (handles unknown aliases).
    Fallback: small known-alias map + exact match only if OpenAI fails.
    """
    return bool(skill_match_details(cv_skills, required_skills).get("match"))


# =========================
# EXPERIENCE CHECK (months)
# =========================
def check_experience(cv_months, req_type, req_value_months):
    """Compare candidate months against required months."""
    try:
        from app.services.utils_experience import normalize_requirement_months

        cv_months = int(cv_months or 0)
        req_months = normalize_requirement_months(req_value_months)
    except Exception:
        return False

    if req_type == "minimum":
        return cv_months >= req_months

    if req_type == "more_than":
        return cv_months > req_months

    if req_type == "exact":
        return cv_months == req_months

    return True


# =========================
# QUALIFICATION VECTOR MATCH
# =========================
def qualification_vector_match(cv_quals, req_quals):
    if not req_quals:
        return True

    cv_quals = clean_list(cv_quals)
    req_quals = clean_list(req_quals)

    if not cv_quals:
        return False

    cv_embedding_cache = {}

    for req in req_quals:
        try:
            req_vector = get_embedding(req)
            best_score = 0.0

            for cvq in cv_quals:
                if cvq not in cv_embedding_cache:
                    cv_embedding_cache[cvq] = get_embedding(cvq)

                cv_vector = cv_embedding_cache[cvq]
                score = cosine_similarity(req_vector, cv_vector)
                best_score = max(best_score, score)

            if best_score < 0.70:
                return False

        except Exception as e:
            print("Qualification vector match error:", e)
            return False

    return True


# =========================
# MAIN EVALUATION
# =========================
def _format_missing_skills(missing_skills) -> str:
    """Comma-separated missing skills, capped for failure_reason VARCHAR(500)."""
    items = [
        str(s).strip()
        for s in (missing_skills or [])
        if s and str(s).strip()
    ]
    if not items:
        return ""

    # Keep room for the rest of a multi-part rejection reason.
    max_len = 280
    parts: list[str] = []
    used = 0
    omitted = 0
    for skill in items:
        extra = len(skill) + (2 if parts else 0)  # ", "
        if parts and used + extra > max_len:
            omitted += 1
            continue
        if not parts and len(skill) > max_len:
            parts.append(skill[: max_len - 1] + "…")
            used = max_len
            omitted += len(items) - 1
            break
        parts.append(skill)
        used += extra
    text = ", ".join(parts)
    if omitted:
        text = f"{text} (+{omitted} more)"
    return text


def build_rejection_reason(
    *,
    skills_ok: bool,
    qual_ok: bool,
    exp_ok: bool,
    cv_months: int = 0,
    exp_type: str = "minimum",
    exp_value: float | int = 0,
    missing_skills: list | None = None,
) -> str:
    """Human-readable reject reasons from match flags (no OpenAI call)."""
    reasons: list[str] = []

    if not skills_ok:
        missing_text = _format_missing_skills(missing_skills)
        if missing_text:
            reasons.append(f"Required skills not matched (missing: {missing_text})")
        else:
            reasons.append("Required skills not matched")

    if not qual_ok:
        reasons.append("Required qualifications not matched")

    if not exp_ok:
        try:
            required = int(round(float(exp_value or 0)))
        except Exception:
            required = 0
        found = int(cv_months or 0)
        label = (
            "minimum"
            if exp_type == "minimum"
            else "more than"
            if exp_type == "more_than"
            else "exact"
        )
        reasons.append(
            f"Experience below requirement ({found} months found, needs {label} {required} months)"
            if exp_type != "exact"
            else f"Experience does not match exact requirement ({found} months found, needs {required} months)"
        )

    return "; ".join(reasons) if reasons else "Did not meet screening criteria"


def evaluate_candidate(
    cv,
    required_skills,
    required_quals,
    exp_type,
    exp_value,
    include_internships: bool = True,
    target_profession: str = "",
    target_intern_label: str = "",
):
    cv_skills = clean_list(cv.get("skills"))
    cv_quals = cv.get("qualifications", [])

    # Prefer worker-computed months when internships are not attached.
    if cv.get("internships") is None and cv.get("experience_months") is not None:
        try:
            cv_months = int(round(float(cv.get("experience_months") or 0)))
        except Exception:
            cv_months = 0
    else:
        cv_months = resolve_experience_months(
            cv,
            include_internships=include_internships,
            target_profession=target_profession,
            target_intern_label=target_intern_label,
        )

    required_skills = clean_list(required_skills)
    required_quals = required_quals or []

    # Skills: OpenAI first, synonym map only if OpenAI fails
    if len(required_skills) == 0:
        skills_ok = True
        missing_skills: list[str] = []
    else:
        skill_details = skill_match_details(cv_skills, required_skills)
        skills_ok = bool(skill_details.get("match"))
        missing_skills = list(skill_details.get("missing") or [])

    # Experience (compare in months)
    exp_ok = check_experience(cv_months, exp_type, exp_value)

    # Qualifications
    if not required_quals:
        qual_ok = True
    else:
        ai_result = normalize_and_match_qualifications(cv_quals, required_quals)
        qual_ok = ai_result["match"] if isinstance(ai_result, dict) else False

        if not qual_ok:
            qual_ok = qualification_vector_match(cv_quals, required_quals)

    # Score
    score = 0

    if skills_ok:
        score += 40

    if qual_ok:
        score += 40

    if exp_ok:
        score += 20

    matched = score == 100
    failure_reason = (
        ""
        if matched
        else build_rejection_reason(
            skills_ok=skills_ok,
            qual_ok=qual_ok,
            exp_ok=exp_ok,
            cv_months=cv_months,
            exp_type=exp_type,
            exp_value=exp_value,
            missing_skills=missing_skills,
        )
    )

    return {
        "match": matched,
        "score": score,
        "skills_ok": skills_ok,
        "qual_ok": qual_ok,
        "exp_ok": exp_ok,
        "missing_skills": missing_skills,
        "failure_reason": failure_reason,
    }
