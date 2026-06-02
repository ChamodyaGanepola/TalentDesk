from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def normalize_and_match_qualifications(cv_quals, required_quals):
    """
    LENIENT QUALIFICATION MATCHER:
    - Treats different degree names as equivalent if related
    - Allows semantic matching (not strict string match)
    - Extra CV qualifications are OK
    """

    if not required_quals:
        return {"match": True, "reason": "No required qualifications"}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
You are a VERY LENIENT qualification matcher.

IMPORTANT RULES:
- Do NOT require exact wording match
- Treat similar degrees as equivalent
- Focus on meaning, not names
- Be flexible with academic titles

Example equivalences:
- Computer Science ≈ Software Engineering ≈ IT ≈ Information Systems
- Electrical Engineering ≈ Electronics Engineering
- Business Management ≈ Business Administration
- Data Science ≈ Computer Science ≈ AI

Rules:
- If CV has a related field, consider it MATCH
- Ignore small naming differences
- Only reject if completely unrelated field

Return ONLY JSON:
{
  "match": true/false,
  "reason": ""
}
"""
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "cv_qualifications": cv_quals,
                        "required_qualifications": required_quals
                    })
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)

        return {
            "match": bool(result.get("match", False)),
            "reason": result.get("reason", "")
        }

    except Exception as e:
        return {
            "match": False,
            "reason": f"openai_error: {str(e)}"
        }