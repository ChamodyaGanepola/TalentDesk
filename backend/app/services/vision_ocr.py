import fitz
import base64
import os
import json
import re
from openai import OpenAI
from app.services.utils_experience import calculate_experience

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "8"))


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


def pdf_to_images(file_path: str):
    doc = fitz.open(file_path)
    images = []

    for page_index, page in enumerate(doc):
        if page_index >= MAX_OCR_PAGES:
            break

        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("jpeg")
        images.append(img_bytes)

    doc.close()
    return images


def image_to_base64(img_bytes):
    return base64.b64encode(img_bytes).decode()


def safe_json_load(text: str):
    try:
        text = text.strip()

        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        print("JSON parse error:", e)
        print("RAW:", text)
        return None


def vision_ocr(file_path: str):
    try:
        images = pdf_to_images(file_path)

        if not images:
            return default_cv_result()

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
            model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
You are a professional CV extraction engine for recruitment screening.

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

RULES:

1. EXPERIENCE:
- Do not calculate final experience.
- Extract only real internships and paid jobs into internships.
- Do not count projects, university assignments, hackathons, or academic work.

2. INTERNSHIPS/JOBS FORMAT:
[
  {
    "type": "internship" or "job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM",
    "end_date": "YYYY-MM or present"
  }
]

3. SKILLS:
- Extract all technical skills from any section.
- Include skills from projects, internships, jobs, and technical summaries.
- Normalize to lowercase.
- Remove duplicates.

4. QUALIFICATIONS:
- Include degrees, diplomas, certifications, and professional qualifications.

5. CONTACT NUMBER:
- Extract primary phone/mobile number exactly as written.
- Include country code if present.
- Return as a string.

6. MULTI-PAGE:
- Combine all pages.
- Remove duplicates.

OUTPUT:
- JSON only.
- No markdown.
- No explanation.
"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract full CV accurately from all pages."
                        },
                        *image_payload
                    ]
                }
            ]
        )

        raw_content = response.choices[0].message.content
        data = safe_json_load(raw_content)

        if not data:
            return default_cv_result()

        internships = data.get("internships", [])
        calculated_exp = calculate_experience(internships)
        direct_exp = parse_float(data.get("experience_years"))
        final_exp = calculated_exp if calculated_exp > 0 else direct_exp

        return {
            "name": str(data.get("name") or "").strip(),
            "email": str(data.get("email") or "").strip(),
            "contact_no": str(data.get("contact_no") or "").strip(),
            "skills": clean_list(data.get("skills", []), lowercase=True),
            "experience_years": final_exp,
            "qualifications": clean_list(data.get("qualifications", []), lowercase=False),
            "profession": str(data.get("profession") or "").strip(),
            "internships": internships if isinstance(internships, list) else []
        }

    except Exception as e:
        print("Vision OCR error:", e)
        return default_cv_result()