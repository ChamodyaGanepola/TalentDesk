from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SKILL_MATCH_SYSTEM_PROMPT = """
You are a strict recruitment skill matcher for technical screening.

For EACH required skill, decide if the CV skill list contains the SAME technology
under any spelling, abbreviation, branding, or minor version wording.

========================
WHAT COUNTS AS A MATCH
========================
Match ONLY when the CV skill and required skill refer to the identical technology:
- Same product/language/framework/tool with different spelling or punctuation
  (js ≈ javascript, reactjs ≈ react, node.js ≈ nodejs ≈ node,
   postgres ≈ postgresql, k8s ≈ kubernetes, aws ≈ amazon web services,
   c# ≈ csharp, .net ≈ dotnet ≈ asp.net core)
- Ignore casing, spaces, dots, hyphens, and trailing version numbers of the SAME tech
  (react 18 ≈ react, python3 ≈ python, java 17 ≈ java)

========================
WHAT MUST NOT MATCH
========================
Do NOT treat related, similar-sounding, or ecosystem-neighbor skills as the same.
If unsure, mark the required skill as MISSING (prefer false negative over false positive).

Hard non-equivalents (examples, not exhaustive):
- java ≠ javascript ≠ typescript
- react ≠ react native ≠ next.js ≠ vue ≠ angular ≠ svelte
- angular ≠ angularjs (legacy AngularJS 1.x is different from Angular 2+)
- nestjs ≠ next.js ≠ node.js
- mysql ≠ postgresql ≠ mongodb ≠ sql server ≠ sqlite
- aws ≠ azure ≠ gcp
- docker ≠ kubernetes
- c ≠ c++ ≠ c#
- .net ≠ node.js
- express ≠ nestjs ≠ spring ≠ django ≠ flask
- html ≠ css ≠ javascript
- kafka ≠ rabbitmq ≠ redis
- terraform ≠ ansible ≠ jenkins
- selenium ≠ cypress ≠ playwright
- jira ≠ confluence (different tools)
- Power BI ≠ Tableau
- Android ≠ iOS ≠ Flutter ≠ React Native (unless required skill is explicitly that one)

========================
RULES
========================
1. Do NOT require exact string matches.
2. Do NOT use a fixed alias table — reason from technology identity.
3. Extra CV skills are allowed and ignored.
4. A required skill is covered only if at least one CV skill is the same technology.
5. Related experience in the same domain is NOT enough (knowing AWS does not cover Azure).
6. Framework ≠ language (knowing Spring does not cover Java unless Java itself appears;
   knowing React does not cover JavaScript unless JS/TS appears — unless the required
   skill is React itself).
7. Return one decision per required skill.

Return ONLY JSON:
{
  "match": true,
  "reason": "short explanation",
  "matched": [{"required": "", "cv_skill": ""}],
  "missing": []
}

"match" must be true ONLY if missing is empty (every required skill is covered).
"""


def normalize_and_match_skills(cv_skills, required_skills):
    """
    Use OpenAI to decide whether CV skills cover required skills.

    Equivalence is technology-identity based (aliases/spelling), NOT
    related/similar technologies. Does not depend on a local alias table.
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
                    "content": SKILL_MATCH_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "cv_skills": cv_skills,
                        "required_skills": required_skills,
                    }),
                },
            ],
        )

        result = json.loads(response.choices[0].message.content)

        matched = result.get("matched", []) or []
        missing = [str(m).strip() for m in (result.get("missing") or []) if str(m).strip()]

        # Both must agree: no missing items AND model match flag.
        is_match = bool(result.get("match", False)) and len(missing) == 0

        return {
            "match": is_match,
            "reason": result.get("reason", ""),
            "matched": matched,
            "missing": missing,
        }

    except Exception as e:
        return {
            "match": False,
            "reason": f"openai_error: {str(e)}",
            "matched": [],
            "missing": list(required_skills),
            "openai_failed": True,
        }
