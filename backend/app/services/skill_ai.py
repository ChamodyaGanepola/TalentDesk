from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def normalize_and_match_skills(cv_skills, required_skills):
    """
    Use OpenAI to decide whether CV skills cover required skills,
    including differently named but equivalent skills.
    """

    if not required_skills:
        return {
            "match": True,
            "reason": "No required skills",
            "matched": [],
            "missing": [],
        }

    if not cv_skills:
        return {
            "match": False,
            "reason": "Candidate has no skills",
            "matched": [],
            "missing": list(required_skills),
        }

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_SKILL_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
You are a recruitment skill matcher.

Decide whether the candidate's CV skills satisfy ALL required skills.

Rules:
- Do NOT require exact string matches.
- Treat differently named but equivalent skills as the same.
- Ignore punctuation, spacing, casing, and minor version words.
- Extra CV skills are allowed.
- Reject a required skill only if nothing equivalent appears in the CV skills.

Examples of equivalents:
- js ≈ javascript
- ts ≈ typescript
- react ≈ reactjs ≈ react.js
- next ≈ nextjs ≈ next.js
- node ≈ nodejs ≈ node.js
- c# ≈ csharp ≈ c sharp
- .net ≈ dotnet ≈ asp.net ≈ asp.net core
- postgres ≈ postgresql
- mongo ≈ mongodb
- aws ≈ amazon web services
- k8s ≈ kubernetes

Return ONLY JSON:
{
  "match": true,
  "reason": "",
  "matched": [{"required": "", "cv_skill": ""}],
  "missing": []
}
"""
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "cv_skills": cv_skills,
                        "required_skills": required_skills
                    })
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "match": bool(result.get("match", False)),
            "reason": result.get("reason", ""),
            "matched": result.get("matched", []) or [],
            "missing": result.get("missing", []) or [],
        }

    except Exception as e:
        return {
            "match": False,
            "reason": f"openai_error: {str(e)}",
            "matched": [],
            "missing": list(required_skills),
            "openai_failed": True,
        }
