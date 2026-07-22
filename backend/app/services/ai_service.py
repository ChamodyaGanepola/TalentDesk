import os
import json
import re
from openai import OpenAI
from app.services.utils_experience import (
    calculate_experience_months,
    filter_jobs_and_internships,
    years_to_months,
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


def extract_cv_text(text: str):
    """
    Extract CV information from text-based PDF content.
    Experience is finally calculated in Python from internships/jobs.
    """

    if not text or not text.strip():
        return default_cv_result()

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_CV_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
You are a professional CV extraction engine for recruitment screening.

Return JSON ONLY in this format:

{
  "name": "",
  "email": "",
  "contact_no": "",
  "skills": [],
  "experience_years": 0.0,
  "experience_months": 0,
  "qualifications": [],
  "profession": "",
  "internships": []
}

RULES:

1. SKILLS:
- Extract only technical skills.
- Include programming languages, frameworks, libraries, tools, platforms, databases, cloud tools, and technical software.
- Include skills from work, internships, projects, and technical summary sections.
- Normalize skills to lowercase.
- Remove duplicates.
- IMPORTANT: Treat differently named but equivalent skills as the SAME skill.
  Always return the most common canonical skill name, and do not list aliases separately.
  Examples:
  - js, javascript, java script -> javascript
  - ts, typescript -> typescript
  - react, reactjs, react.js, react js -> react
  - next, nextjs, next.js -> next.js
  - node, nodejs, node.js -> node.js
  - vue, vuejs, vue.js -> vue.js
  - angularjs, angular.js, angular 2+ -> angular
  - express, expressjs, express.js -> express
  - csharp, c sharp, c-sharp, .net c# -> c#
  - dotnet, .net core, asp.net, asp.net core -> .net
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
  - github actions, gitlab ci -> keep as written if distinct tools, otherwise normalize obvious synonyms
- If a skill is clearly the same technology with punctuation/spacing/version differences, merge into one canonical name.
- Prefer short standard industry names over marketing/versioned names (e.g. "react" not "react 18").

2. EXPERIENCE:
- Do not calculate final experience yourself.
- Extract ONLY real internships and paid/full-time/part-time jobs into the internships array.
- NEVER include personal projects, academic projects, university projects, assignments, coursework, hackathons, or capstone work in internships.
- Projects may still contribute skills, but they must NOT appear in internships and must NOT affect experience.
- Set type to exactly "internship" or "job" for every work entry.
- If a CV only lists projects and no jobs/internships, leave internships as [] and experience_years/experience_months as 0.
- Python recalculates total months from internship/job entries only.

3. INTERNSHIPS/JOBS FORMAT:
[
  {
    "type": "internship" or "job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM or YYYY or Month YYYY",
    "end_date": "YYYY-MM or YYYY or Month YYYY or present"
  }
]

4. QUALIFICATIONS:
- Include degrees, diplomas, certificates, and professional qualifications.
- Keep official names where possible.

5. PROFESSION:
- Extract current role/title if available.

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
        calculated_months = calculate_experience_months(internships)

        # Experience months come only from jobs/internships date ranges.
        final_months = calculated_months

        return {
            "name": str(extracted.get("name") or "").strip(),
            "email": str(extracted.get("email") or "").strip(),
            "contact_no": str(extracted.get("contact_no") or "").strip(),
            "skills": clean_list(extracted.get("skills", []), lowercase=True),
            "experience_months": int(final_months),
            "experience_years": round(final_months / 12, 2),
            "qualifications": clean_list(extracted.get("qualifications", []), lowercase=False),
            "profession": str(extracted.get("profession") or "").strip(),
            "internships": internships
        }

    except Exception as e:
        print("CV extraction error:", e)
        return default_cv_result()