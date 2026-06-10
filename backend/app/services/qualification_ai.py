from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def normalize_and_match_qualifications(cv_quals, required_quals):
    """
    Lenient qualification matcher.
    """

    if not required_quals:
        return {
            "match": True,
            "reason": "No required qualifications"
        }

    if not cv_quals:
        return {
            "match": False,
            "reason": "Candidate has no qualifications"
        }

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_QUALIFICATION_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
You are a lenient qualification matcher.

Rules:
- Do not require exact wording.
- Treat similar degrees as equivalent.
- Focus on academic/professional meaning.
- Extra CV qualifications are allowed.
- Reject only if the required qualification and CV qualification are completely unrelated.

Examples:
- Computer Science ≈ Software Engineering ≈ IT ≈ Information Systems
- Electrical Engineering ≈ Electronics Engineering
- Business Management ≈ Business Administration
- Data Science ≈ Computer Science ≈ AI

Return only JSON:

{
  "match": true,
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