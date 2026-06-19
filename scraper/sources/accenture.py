"""
Accenture — scrapes the Accenture India careers portal (elastic vector-search API).
Method: Public POST /api/accenture/elastic/findjobs (multipart form, no key).
Focuses on Strategy & Consulting / Global Network (S&C GN) and strategy/advisory roles.
"""
import time
import re
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.accenture.com/in-en/careers/jobsearch",
}
API_URL = "https://www.accenture.com/api/accenture/elastic/findjobs"

QUERIES = [
    "Management Consulting Analyst",
    "Strategy Analyst",
    "S&C Global Network",
    "Strategy & Consulting",
    "Digital Strategy",
    "Business Transformation Consultant",
    "Growth Strategy",
]

# Titles that signal the genuine strategy/consulting track
KEEP = ("s&c", "gn ", "gn-", "global network", "consult", "strategy", "advisory",
        "transformation", "value", "growth", "management consulting")
# Engineering / BPO-delivery noise to exclude
DROP = ("software", "support engineer", "custom software", "developer", "sap ",
        "record to report", "order to cash", "delivery operations", "operations senior analyst",
        "cloud engineer", "security engineer", "network engineer", "infrastructure",
        "devops", "full stack", "data engineer", "test engineer", "quality auditing", "voice")


def _post(keyword: str, start: int, size: int = 50) -> list[dict]:
    form = {
        "startIndex": str(start), "maxResultSize": str(size), "jobKeyword": keyword,
        "jobCountry": "India", "jobLanguage": "en", "countrySite": "in-en", "sortBy": "1",
        "searchType": "vectorSearch", "enableQueryBoost": "true", "minScore": "0.6",
        "getFeedbackJudgmentEnabled": "true", "useCleanEmbedding": "true", "score": "true",
        "totalHits": "true", "debugQuery": "false", "jobFilters": "[]",
    }
    try:
        resp = requests.post(
            API_URL, files={k: (None, v) for k, v in form.items()},
            headers=HEADERS, timeout=25,
        )
        if resp.status_code != 200:
            print(f"  [Accenture] HTTP {resp.status_code} for '{keyword}'")
            return []
        return resp.json().get("data", [])
    except requests.RequestException as e:
        print(f"  [Accenture] Error for '{keyword}': {e}")
        return []


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()
    for query in QUERIES:
        for start in (0, 50):
            data = _post(query, start)
            if not data:
                break
            for j in data:
                rid = j.get("requisitionId", "")
                title = j.get("title", "")
                t = title.lower()
                if not rid or rid in seen:
                    continue
                if any(d in t for d in DROP):
                    continue
                if not any(k in t for k in KEEP):
                    continue
                if not is_relevant(title):
                    continue
                seen.add(rid)
                results.append(_normalise(j))
            time.sleep(0.4)
    return results


def _normalise(j: dict) -> dict:
    locs = j.get("location", [])
    location = ", ".join(locs) if isinstance(locs, list) else (j.get("feedCity") or "India")
    yoe = j.get("yearsOfExperience", "")
    level = j.get("careerLevel", "")
    url = (j.get("jobDetailUrl", "") or "").replace("{0}", "in-en")
    # Surface level + years in the description so the AI scorer can weigh seniority
    desc = f"[{level} | {yoe}] " + (j.get("qualificationClean", "") or j.get("jobDescriptionClean", "") or "")
    return {
        "title": j.get("title", ""),
        "company": "Accenture",
        "location": location or "India",
        "url": url,
        "description": desc[:500],
        "source": "Accenture",
        "search_query": "S&C / Strategy",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": j.get("postedDateText", ""),
    }
