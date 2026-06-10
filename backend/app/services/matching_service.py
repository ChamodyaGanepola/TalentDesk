from app.services.vector_service import get_embedding, cosine_similarity
from app.services.qualification_ai import normalize_and_match_qualifications
from difflib import get_close_matches
from sqlalchemy import text
from app.db_mysql import SessionLocal

# =========================
# SKILL ONTOLOGY CACHE
# =========================
SKILL_ALIAS_MAP = {}
CANONICAL_SKILLS = set()
ALIASES_LOADED = False


def load_skill_aliases():
    global SKILL_ALIAS_MAP, CANONICAL_SKILLS, ALIASES_LOADED

    db = SessionLocal()

    try:
        rows = db.execute(text("""
            SELECT canonical, alias FROM skill_aliases
        """)).fetchall()

        alias_map = {}
        canonical_set = set()

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
        SKILL_ALIAS_MAP = {}
        CANONICAL_SKILLS = set()
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
    ensure_aliases_loaded()

    value = str(skill or "").lower().strip()

    if not value:
        return ""

    return SKILL_ALIAS_MAP.get(value, value)


# =========================
# SKILL MATCH
# =========================
def skill_match(
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
        # 1. Exact/canonical match
        if req_skill in cv_skills_normalized:
            continue

        # 2. Fuzzy match
        fuzzy_matches = get_close_matches(
            req_skill,
            list(cv_skills_normalized),
            n=1,
            cutoff=fuzzy_threshold
        )

        if fuzzy_matches:
            continue

        # 3. Substring fallback before embeddings
        substring_found = any(
            req_skill in cv_skill or cv_skill in req_skill
            for cv_skill in cv_skills_normalized
        )

        if substring_found:
            continue

        # 4. Semantic match
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


# =========================
# EXPERIENCE CHECK
# =========================
def check_experience(cv_exp, req_type, req_value):
    try:
        cv_exp = float(cv_exp or 0)
        req_value = float(req_value or 0)
    except Exception:
        return False

    if req_type == "minimum":
        return cv_exp >= req_value

    if req_type == "more_than":
        return cv_exp > req_value

    if req_type == "exact":
        return abs(cv_exp - req_value) < 0.01

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
    cv_exp = float(cv.get("experience_years") or 0)

    required_skills = clean_list(required_skills)
    required_quals = required_quals or []

    # Skills
    skills_ok = len(required_skills) == 0 or skill_match(cv_skills, required_skills)

    # Experience
    exp_ok = check_experience(cv_exp, exp_type, exp_value)

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