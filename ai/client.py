"""Gemini REST client with automatic model fallback on quota exhaustion."""
import json
import os
import time
import requests

_last_call: float = 0.0

MODEL_FALLBACK = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]


def generate(prompt: str, model: str = "", rate_limit: float = 7.0) -> dict:
    """Call Gemini with auto-fallback on 429. Returns parsed JSON dict or {}."""
    global _last_call

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {}

    elapsed = time.time() - _last_call
    if elapsed < rate_limit:
        time.sleep(rate_limit - elapsed)
    _last_call = time.time()

    models = [model] + [m for m in MODEL_FALLBACK if m != model] if model else MODEL_FALLBACK

    for m in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{m}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                return _parse_response(resp)
            if resp.status_code in (429, 404):
                print(f"  [Gemini] {resp.status_code} on {m}, trying next model...")
                time.sleep(2)
                continue
            print(f"  [Gemini] HTTP {resp.status_code} on {m}")
            return {}
        except requests.RequestException as e:
            print(f"  [Gemini] Request error on {m}: {e}")
            return {}

    print("  [Gemini] All models exhausted")
    return {}


def _parse_response(resp: requests.Response) -> dict:
    try:
        text = (
            resp.json()
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError):
        return {}
