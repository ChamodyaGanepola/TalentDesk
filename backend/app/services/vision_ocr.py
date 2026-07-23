import fitz
import base64
import os
import json
import re
from openai import OpenAI
from app.services.utils_experience import (
    filter_jobs_and_internships,
    parse_include_internships,
    profession_intern_label,
    resolve_experience_months,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "8"))


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


def vision_ocr(file_path: str, include_internships: bool = True, target_profession: str = ""):
    try:
        images = pdf_to_images(file_path)

        if not images:
            return default_cv_result()

        include_internships = parse_include_internships(include_internships)
        target = " ".join(str(target_profession or "").strip().split())
        intern_label = profession_intern_label(target)
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
                    "content": f"""
You are a professional CV extraction engine for recruitment screening.

Return ONLY valid JSON:

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

1. EXPERIENCE:
- Do not calculate final experience.
- Extract ONLY real internships and paid/full-time/part-time jobs into internships.
- NEVER include personal/academic/university projects, assignments, coursework, hackathons, or capstones in internships.
- Projects can contribute skills only; they must not affect experience months.
- Set type to exactly "internship" or "job".
- Always extract internships when present, even if they will not count toward months.
- INTERNSHIP EXPERIENCE POLICY FOR THIS BATCH: {internship_policy}
- If there are no jobs/internships, leave internships as [] and experience fields as 0.
- Python recalculates months from work entries according to the internship policy above.

2. INTERNSHIPS/JOBS FORMAT:
[
  {{
    "type": "internship" or "job",
    "company": "",
    "role": "",
    "start_date": "YYYY-MM",
    "end_date": "YYYY-MM or present"
  }}
]

3. SKILLS:
- Extract all technical skills from any section.
- Include skills from projects, internships, jobs, and technical summaries.
- Normalize to lowercase.
- Remove duplicates.
- Canonicalize ONLY when it is the SAME technology with different spelling/punctuation/abbreviation.
  Safe merges: js→javascript, ts→typescript, reactjs→react, nextjs→next.js,
  nodejs→node.js, postgres→postgresql, mongo→mongodb, k8s→kubernetes,
  aws/amazon web services→aws, csharp→c#, html5→html, css3→css, cicd→ci/cd.
- NEVER merge different technologies. Keep separate: java≠javascript≠typescript,
  react≠react native≠next.js≠vue≠angular≠nestjs, mysql≠postgresql≠mongodb,
  aws≠azure≠gcp, docker≠kubernetes, c≠c++≠c#, github actions≠gitlab ci.
- Prefer short standard names over versioned names of the SAME tech (react not react 18).
- If unsure whether two names are the same technology, keep them as separate skills.

4. QUALIFICATIONS:
- Include degrees, diplomas, certifications, and professional qualifications.

5. PROFESSION:
- Extract current role/title if available.
- SCREENING POSITION CONTEXT: {profession_context}

6. CONTACT NUMBER:
- Extract primary phone/mobile number exactly as written.
- Include country code if present.
- Return as a string.

7. MULTI-PAGE:
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

        internships = filter_jobs_and_internships(data.get("internships", []))
        final_months = resolve_experience_months(
            data,
            internships=internships,
            include_internships=include_internships,
            target_profession=target,
        )

        return {
            "name": str(data.get("name") or "").strip(),
            "email": str(data.get("email") or "").strip(),
            "contact_no": str(data.get("contact_no") or "").strip(),
            "skills": clean_list(data.get("skills", []), lowercase=True),
            "experience_months": int(final_months),
            "experience_years": round(final_months / 12, 2),
            "qualifications": clean_list(data.get("qualifications", []), lowercase=False),
            "profession": str(data.get("profession") or "").strip(),
            "internships": internships,
            "include_internships": include_internships,
        }

    except Exception as e:
        print("Vision OCR error:", e)
        return default_cv_result()
