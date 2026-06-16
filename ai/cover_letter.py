"""Generate a tailored, honest cover letter for a job using Gemini + the CV profile."""
import os
import requests

from ai.client import MODEL_FALLBACK

# Plain-text generation (not JSON) — reuses the Gemini REST endpoint directly.
def _generate_text(prompt: str, rate_limit: float = 7.0) -> str:
    import time
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return ""

    for m in MODEL_FALLBACK:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{m}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200},
        }
        try:
            resp = requests.post(url, json=payload, timeout=40)
            if resp.status_code == 200:
                return (
                    resp.json()
                    .get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
            if resp.status_code in (429, 404, 503):
                time.sleep(2)
                continue
            return ""
        except requests.RequestException:
            return ""
    return ""


def generate_cover_letter(job: dict, jd_text: str, context: str) -> str:
    """
    Build a one-page, tailored cover letter.
    `job` must have title, company, location. `jd_text` is the full job description.
    `context` is the candidate profile (profile/context.md).
    """
    prompt = f"""You are an expert career writer. Write a tailored, one-page cover letter for the candidate below applying to the job below.

# Candidate Profile
{context[:1800]}

# Job
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}

# Full Job Description
{jd_text[:3000] if jd_text else "Not available — rely on the title and company."}

# Rules
- Open with the specific role and a hook that ties the candidate's current work to the job's core mandate.
- Use 2-3 concrete, quantified achievements from the profile that map to THIS job's responsibilities.
- Be honest: do NOT invent experience or overstate years. If there is an obvious gap (e.g. required years), lean on transferable strengths instead of claiming the years.
- Professional, confident, concise — no clichés, no "I am writing to express my interest in".
- Around 280-350 words of body text.
- End with a warm, forward-looking close.
- Output ONLY the letter body (greeting through sign-off). Do not include the address header or markdown headings.
"""
    return _generate_text(prompt)
