import os
import json
import re
from openai import OpenAI
from app.services.utils_experience import (
    filter_jobs_and_internships,
    parse_include_internships,
    resolve_experience_months,
    resolve_intern_label,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_float(value):
    try:
        return float(value or 0)
    except Exception:
        match = re.search(r"\d+(\.\d+)?", str(value))
        return float(match.group()) if match else 0.0


def clean_list(values, lowercase=False):
    cleaned = []

    for value in values or []:
        if not value:
            continue

        item = str(value).strip()

        if not item:
            continue

        if lowercase:
            item = item.lower()

        if item not in cleaned:
            cleaned.append(item)

    return cleaned


def default_cv_result():
    return {
        "name": "",
        "email": "",
        "contact_no": "",
        "skills": [],
        "experience_months": 0,
        "experience_years": 0.0,
        "qualifications": [],
        "profession": "",
        "internships": []
    }


def extract_cv_text(
    text: str,
    include_internships: bool = True,
    target_profession: str = "",
    target_intern_label: str = "",
):
    """
    Extract CV information from text-based PDF content.
    Experience is finally calculated in Python from jobs
    (and internships only when include_internships is True).
    target_profession is informational context only — not used for matching.
    """

    if not text or not text.strip():
        return default_cv_result()

    include_internships = parse_include_internships(include_internships)
    target = " ".join(str(target_profession or "").strip().split())
    intern_label = resolve_intern_label(target, target_intern_label)
    internship_policy = (
        f'INCLUDE "{intern_label}" experience in months. Count internship '
        f"entries whose role relates to \"{target or 'the target position'}\" "
        "(and generic internships for that track). Jobs always count."
        if include_internships
        else f'DO NOT include "{intern_label}" (or other internship) months. '
        "Still extract internship entries with type \"internship\", but only "
        'type "job" counts toward experience. Python enforces this.'
    )
    profession_context = (
        f'Target hiring position for this batch: "{target}". '
        "This is informational only for screening context and naming "
        f'(related intern title: "{intern_label}"). '
        "Still extract the candidate's own profession/title from the CV. "
        "Do NOT reject or filter the CV based on title match. "
        "Matching is done separately on skills, qualifications, and experience only."
        if target
        else "No target hiring position was specified for this batch. "
        "Extract the candidate's profession/title from the CV if available."
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_CV_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are a professional CV extraction engine for recruitment screening.

Return JSON ONLY in this format:

{{
  "name": "",
  "email": "",
  "contact_no": "",
  "skills": [],
  "experience_years": 0.0,
  "experience_months": 0,
  "qualifications": [],
  "profession": "",
  "internships": []
}}

RULES:

1. SKILLS:
- Extract only technical skills.
- Include programming languages, frameworks, libraries, tools, platforms, databases, cloud tools, and technical software.
- Include skills from work, internships, projects, and technical summary sections.
- Normalize skills to lowercase.
- Remove duplicates.
- Canonicalize ONLY when it is the SAME technology with different spelling/punctuation/abbreviation.
  Return one common industry name; do not list aliases twice.
  Safe merges:
  - js, javascript, java script -> javascript
  - ts, typescript -> typescript
  - react, reactjs, react.js, react js -> react
  - next, nextjs, next.js -> next.js
  - node, nodejs, node.js -> node.js
  - vue, vuejs, vue.js -> vue.js
  - express, expressjs, express.js -> express
  - csharp, c sharp, c-sharp -> c#
  - postgres, postgresql, postgre sql -> postgresql
  - mongo, mongodb, mongo db -> mongodb
  - mssql, sql server, microsoft sql server -> sql server
  - html5 -> html
  - css3 -> css
  - aws, amazon web services -> aws
  - gcp, google cloud, google cloud platform -> gcp
  - azure, microsoft azure -> azure
  - k8s, kubernetes -> kubernetes
  - ci/cd, cicd -> ci/cd
- NEVER merge different technologies, even if related or similar-sounding.
  Keep these SEPARATE (examples):
  - java ≠ javascript ≠ typescript
  - react ≠ react native ≠ next.js ≠ vue ≠ angular ≠ nestjs
  - angularjs (1.x) ≠ angular (2+)
  - mysql ≠ postgresql ≠ mongodb ≠ sql server
  - aws ≠ azure ≠ gcp
  - docker ≠ kubernetes
  - c ≠ c++ ≠ c#
  - github actions ≠ gitlab ci (distinct tools — keep both if both appear)
- Prefer short standard names over versioned names of the SAME tech (react not react 18).
- If unsure whether two names are the same technology, keep them as separate skills.

2. EXPERIENCE:
- Do not calculate final experience yourself.
- Extract ONLY real internships and paid/full-time/part-time jobs into the internships array.
- NEVER include personal projects, academic projects, university projects, assignments, coursework, hackathons, or capstone work in internships.
- Projects may still contribute skills, but they must NOT appear in internships and must NOT affect experience.
- Set type to exactly "internship" or "job" for every work entry.
- Always extract internships when present, even if they will not count toward months.
- INTERNSHIP EXPERIENCE POLICY FOR THIS BATCH: {internship_policy}
- If a CV only lists projects and no jobs/internships, leave internships as [] and experience_years/experience_months as 0.
- Python recalculates total months from work entries according to the internship policy above.

3. INTERNSHIPS/JOBS FORMAT:
[
  {{
    "type": "internship" or "job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM or YYYY or Month YYYY",
    "end_date": "YYYY-MM or YYYY or Month YYYY or present"
  }}
]

4. QUALIFICATIONS:
- Include degrees, diplomas, certificates, and professional qualifications.
- Keep official names where possible.

5. PROFESSION:
- Extract current role/title if available.
- SCREENING POSITION CONTEXT: {profession_context}

6. CONTACT:
- Extract primary phone/mobile number exactly as written.
- Include country code if present.
- Return as a string.

OUTPUT:
- Valid JSON only.
- No markdown.
- No explanation.
"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        raw_content = response.choices[0].message.content

        print("===== GPT RAW RESPONSE =====")
        print(raw_content)
        print("============================")

        extracted = json.loads(raw_content)

        # Only jobs/internships count — drop projects and other non-work items.
        internships = filter_jobs_and_internships(extracted.get("internships", []))
        # Prefer date-derived months, but never discard stated years (e.g. years=5, months=0).
        final_months = resolve_experience_months(
            extracted,
            internships=internships,
            include_internships=include_internships,
            target_profession=target,
            target_intern_label=target_intern_label,
        )

        return {
            "name": str(extracted.get("name") or "").strip(),
            "email": str(extracted.get("email") or "").strip(),
            "contact_no": str(extracted.get("contact_no") or "").strip(),
            "skills": clean_list(extracted.get("skills", []), lowercase=True),
            "experience_months": int(final_months),
            "experience_years": round(final_months / 12, 2),
            "qualifications": clean_list(extracted.get("qualifications", []), lowercase=False),
            "profession": str(extracted.get("profession") or "").strip(),
            "internships": internships,
            "include_internships": include_internships,
        }

    except Exception as e:
        print("CV extraction error:", e)
        return default_cv_result()