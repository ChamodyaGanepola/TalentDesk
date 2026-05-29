def evaluate_candidate(cv, required_skills, required_quals, required_exp):

    cv_skills = set([s.lower() for s in cv.get("skills", [])])
    cv_quals = set([q.lower() for q in cv.get("qualifications", [])])

    exp = cv.get("experience_years", 0)

    # RULE 1: ALL required skills must match
    skills_ok = set(required_skills).issubset(cv_skills)

    # RULE 2: experience check (internships included already in OCR text)
    exp_ok = exp >= required_exp

    # RULE 3: at least one qualification match
    qual_ok = len(set(required_quals).intersection(cv_quals)) > 0

    return skills_ok and exp_ok and qual_ok