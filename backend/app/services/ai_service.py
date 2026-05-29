import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_cv_text(text: str):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
You are a CV extraction engine.

Extract ALL information from CV.

Return JSON ONLY:

{
  "name": "",
  "skills": [],
  "experience_years": 0,
  "qualifications": [],
  "profession": "",
  "internships": []
}

Rules:
- NEVER return empty skills if CV has technical content
- infer skills from job descriptions
- internships count as experience
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("JSON parse error:", e)
        print(response.choices[0].message.content)

        return {
            "name": "",
            "skills": [],
            "experience_years": 0,
            "qualifications": [],
            "profession": "",
            "internships": []
        }