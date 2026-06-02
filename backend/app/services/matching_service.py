from app.services.vector_service import get_embedding, cosine_similarity
from app.services.qualification_ai import normalize_and_match_qualifications
from difflib import get_close_matches
# =========================
# CLEAN LIST
# =========================
def clean_list(data):
    if not data:
        return []

    return [
        str(x).strip().lower()
        for x in data
        if x and str(x).strip()
    ]


# =========================
# EXPERIENCE CHECK
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
# VECTOR QUALIFICATION MATCH
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

            print(f"QUAL MATCH -> {req} <-> {cvq} = {score}")

            best_score = max(best_score, score)

        # if any required qualification fails threshold → reject
        if best_score < 0.70:
            return False

    return True

def skill_match(cv_skills, required_skills, threshold=0.8):
    cv_skills_lower = {s.lower() for s in cv_skills}

    for req in required_skills:
        matches = get_close_matches(req.lower(), cv_skills_lower, n=1, cutoff=threshold)
        if not matches:
            return False

    return True
# =========================
# MAIN EVALUATION FUNCTION (FIXED FOR WORKER)
# =========================
def evaluate_candidate(
    cv,
    required_skills,
    required_quals,
    exp_type,
    exp_value
):

    # =========================
    # CV DATA
    # =========================
    cv_skills = set(clean_list(cv.get("skills")))
    cv_quals = cv.get("qualifications", [])
    cv_exp = float(cv.get("experience_years") or 0)
    print("CV Skills:", cv_skills)
    print("CV Qualifications:", cv_quals)
    print("CV Experience:", cv_exp)

    # =========================
    # REQUIRED DATA
    # =========================
    required_skills = set(clean_list(required_skills))
    print("Required Skills:", required_skills)
    required_quals = required_quals or []
    print("Required Qualifications:", required_quals)
    # =========================
    # RULE 1: SKILLS (STRICT MATCH)
    # =========================
    skills_ok = (
     len(required_skills) == 0
     or skill_match(cv_skills, required_skills)
  )

    # =========================
    # RULE 2: EXPERIENCE
    # =========================
    exp_ok = check_experience(cv_exp, exp_type, exp_value)
    print(f"Experience Check: CV={cv_exp} | Type={exp_type} | Required={exp_value}")
    # =========================
    # RULE 3: QUALIFICATIONS (VECTOR MATCH)
    # =========================
   

    ai_result = normalize_and_match_qualifications(cv_quals, required_quals)
    if ai_result["match"]:
       qual_ok = True
    else:
    # fallback to vector logic
       qual_ok = qualification_vector_match(cv_quals, required_quals)

    # =========================
    # FINAL SCORE SYSTEM (SAFE + FLEXIBLE)
    # =========================
    score = 0

    if skills_ok:
        score += 40
    if qual_ok:
        score += 40
    if exp_ok:
        score += 20

    match = score >= 70

    print("\n======================")
    print("MATCH DEBUG")
    print("Skills OK:", skills_ok)
    print("Qual OK:", qual_ok)
    print("Exp OK:", exp_ok)
    print("Score:", score)
    print("MATCH:", match)
    print("======================\n")

    return {
        "match": match,
        "score": score,
        "skills_ok": skills_ok,
        "qual_ok": qual_ok,
        "exp_ok": exp_ok
    }