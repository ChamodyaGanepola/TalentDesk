from app.services.vector_service import get_embedding, cosine_similarity
from app.services.qualification_ai import normalize_and_match_qualifications
from difflib import get_close_matches
from sqlalchemy import text
from app.db_mysql import SessionLocal

# =========================
# SKILL ONTOLOGY (DB CACHE)
# =========================
SKILL_ALIAS_MAP = {}
CANONICAL_SKILLS = set()

def load_skill_aliases():
    """
    Load skill ontology from DB: canonical + alias mapping
    """
    global SKILL_ALIAS_MAP, CANONICAL_SKILLS

    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT canonical, alias FROM skill_aliases")).fetchall()
        SKILL_ALIAS_MAP = {}
        CANONICAL_SKILLS = set()

        for canonical, alias in rows:
            canonical = canonical.lower().strip()
            alias = alias.lower().strip()

            CANONICAL_SKILLS.add(canonical)
            SKILL_ALIAS_MAP[alias] = canonical
            SKILL_ALIAS_MAP[canonical] = canonical

    except Exception as e:
        print("Skill alias load error:", e)
        SKILL_ALIAS_MAP = {}
        CANONICAL_SKILLS = set()

    finally:
        db.close()

# =========================
# CLEAN LIST
# =========================
def clean_list(data):
    if not data:
        return []
    return [str(x).strip().lower() for x in data if x and str(x).strip()]

# =========================
# NORMALIZE SKILL (NEW)
# =========================
def normalize_skill(skill: str) -> str:
    s = skill.lower().strip()
    if s in SKILL_ALIAS_MAP:
        return SKILL_ALIAS_MAP[s]
    return s



# =========================
# SKILL MATCH (LINKEDIN-LEVEL, ATS-FRIENDLY)
# =========================
def skill_match(cv_skills, required_skills, fuzzy_threshold=0.8, semantic_threshold=0.70):
    """
    Matches CV skills to required skills using multiple levels:
    1. Canonical exact match (if canonical DB exists)
    2. Fuzzy match (typos / small variations)
    3. Semantic vector match (embedding similarity)
    4. Substring fallback (last resort)
    """

    # Normalize all CV skills
    cv_skills_normalized = {s.lower().strip() for s in cv_skills if s and s.strip()}
    required_skills_normalized = [s.lower().strip() for s in required_skills if s and s.strip()]

    for req_skill in required_skills_normalized:

        # 1. Canonical exact match (if exists)
        if req_skill in cv_skills_normalized:
            continue

        # 2️ Fuzzy match
        fuzzy_matches = get_close_matches(req_skill, cv_skills_normalized, n=1, cutoff=fuzzy_threshold)
        if fuzzy_matches:
            continue

        # 3. Semantic vector match
        req_vec = get_embedding(req_skill)
        semantic_found = False
        for cv_skill in cv_skills_normalized:
            cv_vec = get_embedding(cv_skill)
            if cosine_similarity(req_vec, cv_vec) >= semantic_threshold:
                semantic_found = True
                break
        if semantic_found:
            continue

        # 4. Substring / keyword fallback
        substring_found = any(req_skill in cv_skill or cv_skill in req_skill for cv_skill in cv_skills_normalized)
        if substring_found:
            continue

        # If none of the above matched, skill not found
        return False

    # All required skills matched at least once
    return True

# =========================
# EXPERIENCE CHECK (UNCHANGED)
# =========================
def check_experience(cv_exp, req_type, req_value):
    try:
        cv_exp = float(cv_exp or 0)
        req_value = float(req_value or 0)
    except:
        return False

    if req_type == "minimum":
        return cv_exp >= req_value
    if req_type == "more_than":
        return cv_exp > req_value
    if req_type == "exact":
        return abs(cv_exp - req_value) < 0.01

    return True

# =========================
# VECTOR QUALIFICATION MATCH (UNCHANGED)
# =========================
def qualification_vector_match(cv_quals, req_quals):
    if not req_quals:
        return True

    cv_quals = clean_list(cv_quals)
    req_quals = clean_list(req_quals)

    for req in req_quals:
        req_vector = get_embedding(req)
        best_score = 0.0
        for cvq in cv_quals:
            cv_vector = get_embedding(cvq)
            score = cosine_similarity(req_vector, cv_vector)
            best_score = max(best_score, score)
        if best_score < 0.70:
            return False
    return True

# =========================
# MAIN EVALUATION FUNCTION (UNCHANGED LOGIC)
# =========================
def evaluate_candidate(cv, required_skills, required_quals, exp_type, exp_value):

    cv_skills = clean_list(cv.get("skills"))
    cv_quals = cv.get("qualifications", [])
    cv_exp = float(cv.get("experience_years") or 0)
    required_skills = clean_list(required_skills)

    # SKILLS
    skills_ok = len(required_skills) == 0 or skill_match(cv_skills, required_skills)

    # EXPERIENCE
    exp_ok = check_experience(cv_exp, exp_type, exp_value)

    # QUALIFICATIONS
    ai_result = normalize_and_match_qualifications(cv_quals, required_quals)
    qual_ok = ai_result["match"] if isinstance(ai_result, dict) else False
    if not qual_ok:
        qual_ok = qualification_vector_match(cv_quals, required_quals)

    # SCORE
    score = 0
    if skills_ok: score += 40
    if qual_ok: score += 40
    if exp_ok: score += 20

    return {
        "match": score == 100,
        "score": score,
        "skills_ok": skills_ok,
        "qual_ok": qual_ok,
        "exp_ok": exp_ok
    }