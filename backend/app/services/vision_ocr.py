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
# MAIN VISION OCR (FIXED)
# =========================
def vision_ocr(file_path: str):

    images = pdf_to_images(file_path)

    # build ALL images in one request
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
You are a professional CV extraction engine.

Extract FULL CV information from ALL provided pages.

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
- Merge data across all pages
- Remove duplicates
- skills MUST be lowercase
- qualifications must be full official names
- internships contribute to experience_years
- NEVER return markdown or explanations
"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract this full CV accurately from all pages."},
                    *image_payload
                ]
            }
        ]
    )

    data = safe_json_load(response.choices[0].message.content)

    # fallback safe return
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

    # final cleanup
    data["skills"] = list(set([s.lower() for s in data.get("skills", [])]))
    data["qualifications"] = list(set(data.get("qualifications", [])))

    return data