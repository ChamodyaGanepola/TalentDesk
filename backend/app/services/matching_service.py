from app.services.vector_service import get_embedding, cosine_similarity
from app.services.qualification_ai import normalize_and_match_qualifications
from app.services.skill_ai import normalize_and_match_skills
from app.services.utils_experience import years_to_months
from difflib import get_close_matches
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
# (synonym map + fuzzy + embeddings)
# =========================
def skill_match_fallback(
    cv_skills,
    required_skills,
    fuzzy_threshold=0.8,
    semantic_threshold=0.70
):
    cv_skills_normalized = {
        normalize_skill(skill)
        for skill in cv_skills
        if skill and str(skill).strip()
    }

    required_skills_normalized = [
        normalize_skill(skill)
        for skill in required_skills
        if skill and str(skill).strip()
    ]

    cv_skills_normalized = {s for s in cv_skills_normalized if s}
    required_skills_normalized = [s for s in required_skills_normalized if s]

    if not required_skills_normalized:
        return True

    if not cv_skills_normalized:
        return False

    cv_embedding_cache = {}

    for req_skill in required_skills_normalized:
        if req_skill in cv_skills_normalized:
            continue

        fuzzy_matches = get_close_matches(
            req_skill,
            list(cv_skills_normalized),
            n=1,
            cutoff=fuzzy_threshold
        )

        if fuzzy_matches:
            continue

        substring_found = any(
            req_skill in cv_skill or cv_skill in req_skill
            for cv_skill in cv_skills_normalized
        )

        if substring_found:
            continue

        try:
            req_vec = get_embedding(req_skill)
            semantic_found = False

            for cv_skill in cv_skills_normalized:
                if cv_skill not in cv_embedding_cache:
                    cv_embedding_cache[cv_skill] = get_embedding(cv_skill)

                cv_vec = cv_embedding_cache[cv_skill]

                if cosine_similarity(req_vec, cv_vec) >= semantic_threshold:
                    semantic_found = True
                    break

            if semantic_found:
                continue

        except Exception as e:
            print("Skill semantic match error:", e)

        return False

    return True


def skill_match(cv_skills, required_skills):
    """
    Primary: OpenAI similar-skill matching.
    Fallback: synonym map / fuzzy / embeddings only if OpenAI fails.
    """
    required_skills = clean_list(required_skills)
    cv_skills = clean_list(cv_skills)

    if not required_skills:
        return True

    if not cv_skills:
        return False

    # Fast path: exact string coverage (no synonym map).
    required_set = set(required_skills)
    cv_set = set(cv_skills)
    if required_set.issubset(cv_set):
        return True

    ai_result = normalize_and_match_skills(cv_skills, required_skills)

    if isinstance(ai_result, dict) and not ai_result.get("openai_failed"):
        print(
            "OpenAI skill match:",
            ai_result.get("match"),
            ai_result.get("reason"),
            "missing=",
            ai_result.get("missing"),
        )
        return bool(ai_result.get("match", False))

    print(
        "OpenAI skill match failed; using synonym-map fallback:",
        ai_result.get("reason") if isinstance(ai_result, dict) else ai_result,
    )
    return skill_match_fallback(cv_skills, required_skills)


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
def evaluate_candidate(cv, required_skills, required_quals, exp_type, exp_value):
    cv_skills = clean_list(cv.get("skills"))
    cv_quals = cv.get("qualifications", [])

    if cv.get("experience_months") is not None:
        try:
            cv_months = int(cv.get("experience_months") or 0)
        except Exception:
            cv_months = years_to_months(cv.get("experience_years"))
    else:
        cv_months = years_to_months(cv.get("experience_years"))

    required_skills = clean_list(required_skills)
    required_quals = required_quals or []

    # Skills: OpenAI first, synonym map only if OpenAI fails
    skills_ok = len(required_skills) == 0 or skill_match(cv_skills, required_skills)

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

    return {
        "match": score == 100,
        "score": score,
        "skills_ok": skills_ok,
        "qual_ok": qual_ok,
        "exp_ok": exp_ok
    }
