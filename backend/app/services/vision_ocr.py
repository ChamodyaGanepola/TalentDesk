import fitz
import base64
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def pdf_to_images(file_path: str):
    doc = fitz.open(file_path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))

    return images


def image_to_base64(img_bytes):
    return base64.b64encode(img_bytes).decode()


def vision_ocr(file_path: str):

    images = pdf_to_images(file_path)

    full_result = {
        "name": "",
        "email": "",
        "contact_no": "",
        "skills": [],
        "experience_years": 0.0,
        "qualifications": [],
        "profession": "",
        "internships": [],
        "raw_text": ""   # ✅ FIXED COMMA ISSUE
    }

    for img in images:

        base64_img = image_to_base64(img)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """
Extract CV into STRICT JSON ONLY:

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

Rules:
- Extract email address
- Extract phone number
- Qualifications should contain degrees, diplomas, certifications
- internships MUST be counted in experience_years
- Return ONLY valid JSON
"""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract CV"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_img}"
                            }
                        }
                    ]
                }
            ]
        )

        try:
            data = json.loads(response.choices[0].message.content)

            # =========================
            # MERGE PAGES SAFELY
            # =========================
            full_result["skills"] += data.get("skills", [])
            full_result["qualifications"] += data.get("qualifications", [])

            full_result["experience_years"] = max(
                full_result["experience_years"],
                data.get("experience_years", 0)
            )

            if not full_result["name"]:
                full_result["name"] = data.get("name", "")

            if not full_result["email"]:
                full_result["email"] = data.get("email", "")

            if not full_result["contact_no"]:
                full_result["contact_no"] = data.get("contact_no", "")

            if not full_result["profession"]:
                full_result["profession"] = data.get("profession", "")

        except Exception:
            continue

    # =========================
    # CLEAN DUPLICATES
    # =========================
    full_result["skills"] = list(set(full_result["skills"]))
    full_result["qualifications"] = list(set(full_result["qualifications"]))

    return full_result