import os
import json
from openai import OpenAI
from app.services.utils_experience import calculate_experience  

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
- Extract ALL technical skills(don't extract soft skills) from anywhere in CV.
Include all programming languages, frameworks, libraries, tools, and platforms mentioned in the CV.
Do not exclude any front-end or back-end frameworks, even if they appear in long lists or under "Web Development" sections.
- Include skills from:
  - internships
  - work experience
  - technical summaries
  - project descriptions (ONLY for skills, NOT experience)
  -or anywhere in the CV that indicates a technical skill
- Normalize to lowercase
- Remove duplicates

2. EXPERIENCE RULE:
-If directly mentioned experience in years, use that (but only if it explicitly states it's from internships/jobs)
- If not directly mentioned, calculate experience by summing durations of ALL internships and paid jobs (DO NOT count projects or academic work)
- Convert durations to years:
  3 months = 0.25 years
  6 months = 0.5 years
  1 year = 1.0 years
  1.5 years = 1.5 years

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

CONTACT NUMBER:
- Extract the primary phone/mobile number exactly as written.
- Include country code if present.
- Do NOT modify formatting.
- If multiple numbers exist, return the candidate's primary contact number.
- Return as a string.
"""
            },
            {"role": "user", "content": text}
        ]
    )
    print("===== GPT RAW RESPONSE =====")
    print(response.choices[0].message.content)
    print("============================")

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