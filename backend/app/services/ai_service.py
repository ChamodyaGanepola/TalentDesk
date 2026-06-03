import os
import json
from openai import OpenAI
from app.services.utils_experience import calculate_experience  # ✅ import the common function

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_cv_text(text: str):
    """
    Extract CV information using GPT and calculate experience precisely
    counting only internships and paid jobs.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
You are a professional CV extraction engine for recruitment screening.

Extract ALL information from the CV text accurately.

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

========================
RULES (VERY IMPORTANT)
========================

1. SKILLS:
- Extract ALL technical skills(don't extract soft skills) from anywhere in CV
- Include skills from:
  - internships
  - work experience
  - technical summaries
  - project descriptions (ONLY for skills, NOT experience)
  -or anywhere in the CV
- Remove duplicates

2. EXPERIENCE RULE:
- ONLY internships + paid jobs
- DO NOT include projects or academic work

3. INTERNSHIPS FORMAT:
[
  {
    "type": "internship/job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM or YYYY or Month YYYY",
    "end_date": "YYYY-MM or present"
  }
]
 IMPORTANT:
- NEVER calculate experience here
- NEVER round numbers

3. QUALIFICATIONS:
- Include all type of degrees, diplomas, certifications
- Keep full official names



5. PROFESSION:
- Extract current role or title if available

6. OUTPUT RULES:
- NEVER round experience_years
- ALWAYS return valid JSON only
- NO markdown, NO explanation
"""
            },
            {"role": "user", "content": text}
        ]
    )

    try:
        # parse GPT JSON
        extracted = json.loads(response.choices[0].message.content)

        # =========================
        # Calculate total experience using utils_experience
        # only internships/jobs counted
        
    # CALCULATE EXPERIENCE IN PYTHON (IMPORTANT FIX)
        extracted["experience_years"] = calculate_experience(extracted.get("internships", []))

        # cleanup skills & qualifications
        extracted["skills"] = list(set([s.lower().strip() for s in extracted.get("skills", [])]))
        extracted["qualifications"] = list(set(extracted.get("qualifications", [])))
        

        return extracted

    except Exception as e:
        print("JSON parse error:", e)
        print(response.choices[0].message.content)

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