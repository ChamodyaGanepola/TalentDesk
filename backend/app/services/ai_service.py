import os
import json
import re
from openai import OpenAI
from app.services.utils_experience import calculate_experience

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

2. EXPERIENCE:
- Do not calculate final experience yourself.
- Extract real internships and paid jobs only into the internships array.
- Do not include projects, assignments, academic work, or hackathons as experience.
- If a direct total experience is clearly written, place it in experience_years, but Python will recalculate using internships/jobs.

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

        internships = extracted.get("internships", [])
        calculated_exp = calculate_experience(internships)

        # If internships were not detected but CV has direct experience text,
        # keep direct value as fallback.
        direct_exp = parse_float(extracted.get("experience_years"))
        final_exp = calculated_exp if calculated_exp > 0 else direct_exp

        return {
            "name": str(extracted.get("name") or "").strip(),
            "email": str(extracted.get("email") or "").strip(),
            "contact_no": str(extracted.get("contact_no") or "").strip(),
            "skills": clean_list(extracted.get("skills", []), lowercase=True),
            "experience_years": final_exp,
            "qualifications": clean_list(extracted.get("qualifications", []), lowercase=False),
            "profession": str(extracted.get("profession") or "").strip(),
            "internships": internships if isinstance(internships, list) else []
        }

    except Exception as e:
        print("CV extraction error:", e)
        return default_cv_result()