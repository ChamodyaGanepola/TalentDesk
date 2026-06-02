from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def normalize_and_match_qualifications(cv_quals, required_quals):

    if not required_quals:
        return True

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """
You are a qualification matching engine.

Your job:
- Determine if CV qualifications satisfy required qualifications
- Treat equivalent degrees as MATCH

Examples:
- Computer Science ≈ Software Engineering ≈ IT ≈ Information Systems
- Electrical Engineering ≈ Electronics Engineering
- Business Management ≈ Business Administration

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

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"match": False, "reason": "parse_error"}