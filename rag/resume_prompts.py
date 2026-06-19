EXTRACT_PROMPT = """
You are an expert HR assistant. Extract structured information from the resume below.
Return ONLY a valid JSON object with no explanation, no markdown, no backticks.

Resume:
{resume_text}

Return this exact JSON structure:
{{
    "name": "full name of candidate",
    "email": "email address or null",
    "phone": "phone number or null",
    "total_experience_years": 0,
    "skills": ["skill1", "skill2"],
    "education": "highest degree and institution",
    "previous_roles": ["role1", "role2"],
    "languages": ["language1"]
}}
"""

SCORE_PROMPT = """
You are an expert HR screener. Score the candidate against the job description below.
Return ONLY a valid JSON object with no explanation, no markdown, no backticks.

Job Description:
{jd}

Candidate Resume:
{resume_text}

Return this exact JSON structure:
{{
    "name": "candidate name",
    "match_score": 0,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "experience_match": true,
    "summary": "2-3 sentence summary of fit",
    "recommendation": "Strong Match / Good Match / Partial Match / Not Recommended"
}}

match_score must be an integer from 0 to 100.
"""

COMPARE_PROMPT = """
You are an expert HR screener. Compare these two candidates for the given job description.
Return ONLY a valid JSON object with no explanation, no markdown, no backticks.

Job Description:
{jd}

Candidate A - {name_a}:
{resume_a}

Candidate B - {name_b}:
{resume_b}

Return this exact JSON structure:
{{
    "winner": "name of better candidate",
    "reason": "2-3 sentence explanation",
    "candidate_a": {{
        "name": "{name_a}",
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "score": 0
    }},
    "candidate_b": {{
        "name": "{name_b}",
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "score": 0
    }}
}}
"""

SKILL_GAP_PROMPT = """
You are an expert HR analyst. Analyze the skill gap for this candidate against the job description.
Return ONLY a valid JSON object with no explanation, no markdown, no backticks.

Job Description:
{jd}

Candidate:
{resume_text}

Return this exact JSON structure:
{{
    "name": "candidate name",
    "has_skills": ["skill1", "skill2"],
    "missing_critical": ["critical missing skill1"],
    "missing_nice_to_have": ["nice to have skill1"],
    "upskilling_suggestions": ["suggestion1", "suggestion2"],
    "readiness": "Ready Now / 3-6 Months / 6-12 Months / Not Suitable"
}}
"""