import fitz
import base64
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# PDF → IMAGES
# =========================
def pdf_to_images(file_path: str):
    doc = fitz.open(file_path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("jpeg")
        images.append(img_bytes)

    return images


# =========================
# BASE64 ENCODER
# =========================
def image_to_base64(img_bytes):
    return base64.b64encode(img_bytes).decode()


# =========================
# SAFE JSON PARSER
# =========================
def safe_json_load(text: str):
    try:
        text = text.strip()

        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        print("❌ JSON parse error:", e)
        print("RAW:", text)
        return None


# =========================
# MAIN VISION OCR (IMPROVED)
# =========================
def vision_ocr(file_path: str):

    images = pdf_to_images(file_path)

    image_payload = []

    for img in images:
        base64_img = image_to_base64(img)

        image_payload.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_img}"
            }
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
You are a professional CV extraction engine for recruitment screening.

Extract FULL CV information from ALL pages.

Return ONLY valid JSON:

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
CRITICAL RULES
========================

1. EXPERIENCE (VERY IMPORTANT):
- ONLY count:
  ✔ internships
  ✔ real job experience

- DO NOT count:
  ✘ projects
  ✘ university assignments
  ✘ hackathons (unless internship/job)

- Convert:
  3 months = 0.25
  6 months = 0.5
  1 year = 1.0
  1.5 years = 1.5

- SUM all internships + jobs

2. SKILLS:
- Extract ALL technical skills from ANY section
- MUST include skills from:
  - projects (ONLY for skill extraction)
  - internships
  - work experience
- Normalize to lowercase
- Remove duplicates

3. QUALIFICATIONS:
- Include degrees, diplomas, certifications
- Keep full official names
4. INTERNSHIPS / JOBS FORMAT (CRITICAL):

Extract ONLY real work experience:

✔ internships
✔ paid jobs

DO NOT include:
✘ projects
✘ university work
✘ hackathons

Return format:

"internships": [
  {
    "type": "internship" or "job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM",
    "end_date": "YYYY-MM or present"
  }
]

Rules:
- Convert all dates to YYYY-MM format
- If only year exists (2024), convert to 2024-01
- If month not known, assume 01
- If “Present” or similar to "current"→ use "present"
- Do NOT calculate experience here




========================
MERGE RULE
========================
If multiple pages:
- Combine all data
- Remove duplicates
"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract full CV accurately from all pages."},
                    *image_payload
                ]
            }
        ]
    )

    data = safe_json_load(response.choices[0].message.content)

    # =========================
    # FALLBACK
    # =========================
    if not data:
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

    # =========================
    # CLEANUP
    # =========================
    data["skills"] = list(set([s.lower().strip() for s in data.get("skills", [])]))
    data["qualifications"] = list(set(data.get("qualifications", [])))

    return data