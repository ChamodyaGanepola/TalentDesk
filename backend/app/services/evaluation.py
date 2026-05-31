# app/services/evaluation.py

def clean_list(data):
    """
    Converts:
    ["", " "] → []
    ["Python", ""] → ["python"]
    """
    if not data:
        return []

    return [
        str(x).lower().strip()
        for x in data
        if x and str(x).strip()
    ]


# =========================
# EXPERIENCE CHECK (PURE LOGIC)
# =========================
def check_experience(cv_exp, req_type, req_value):

    try:
        cv_exp = float(cv_exp or 0)
        req_value = float(req_value or 0)
    except:
        cv_exp = 0
        req_value = 0

    if req_type == "minimum":
        return cv_exp >= req_value

    if req_type == "more_than":
        return cv_exp > req_value

    if req_type == "exact":
        return abs(cv_exp - req_value) < 0.01  # float safe

    return True


# =========================
# MAIN EVALUATION FUNCTION
# =========================
def evaluate_candidate(cv, required_skills, required_quals, required_exp):

    print("\n==============================")
    print("EVALUATION START")
    print("==============================")

    # =========================
    # CV DATA
    # =========================
    cv_skills = set(clean_list(cv.get("skills")))
    cv_quals = set(clean_list(cv.get("qualifications")))

    try:
        cv_exp = float(cv.get("experience_years") or 0)
    except:
        cv_exp = 0

    print("CV SKILLS:", cv_skills)
    print("CV QUALS:", cv_quals)
    print("CV EXP:", cv_exp)

    # =========================
    # REQUIREMENTS
    # =========================
    required_skills = set(clean_list(required_skills))
    required_quals = set(clean_list(required_quals))

    try:
        required_exp = float(required_exp or 0)
    except:
        required_exp = 0

    print("\nREQUIRED SKILLS:", required_skills)
    print("REQUIRED QUALS:", required_quals)
    print("REQUIRED EXP:", required_exp)

    # =========================
    # RULE 1: SKILLS
    # =========================
    skills_ok = (
        len(required_skills) == 0
        or required_skills.issubset(cv_skills)
    )

    # =========================
    # RULE 2: QUALIFICATIONS
    # =========================
    qual_ok = (
        len(required_quals) == 0
        or len(required_quals.intersection(cv_quals)) > 0
    )

    # =========================
    # RULE 3: EXPERIENCE (MINIMUM ONLY HERE)
    # =========================
    exp_ok = cv_exp >= required_exp

    final = skills_ok and qual_ok and exp_ok

    print("\nSKILLS OK:", skills_ok)
    print("QUAL OK:", qual_ok)
    print("EXP OK:", exp_ok)
    print("FINAL:", final)
    print("==============================\n")

    return final