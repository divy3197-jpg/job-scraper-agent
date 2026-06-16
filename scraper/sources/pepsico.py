"""
PepsiCo — scrapes pepsicojobs.com (Phenom People platform JSON API).
Method: Public Phenom JSON API (no key). Filters to India roles client-side.
"""
import time
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
API_URL = "https://www.pepsicojobs.com/api/jobs"

QUERIES = [
    "strategy",
    "transformation",
    "consultant",
    "business development",
    "operations manager",
    "data analytics",
    "chief of staff",
]


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()
    for query in QUERIES:
        for item in _search(query):
            url = item.get("url", "")
            if url and url not in seen and is_relevant(item.get("title", "") + " " + item.get("description", "")):
                seen.add(url)
                results.append(item)
        time.sleep(1)
    return results


def _search(query: str) -> list[dict]:
    params = {"keywords": query, "page": 1, "sortBy": "relevance", "limit": 30}
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"  [PepsiCo] HTTP {resp.status_code} for '{query}'")
            return []
        jobs = resp.json().get("jobs", [])
    except Exception as e:
        print(f"  [PepsiCo] Error for '{query}': {e}")
        return []

    out = []
    for j in jobs:
        d = j.get("data", j)
        if (d.get("country_code") or "").upper() != "IN":
            continue  # India only
        out.append(_normalise(d, query))
    return out


def _normalise(d: dict, query: str) -> dict:
    req_id = d.get("req_id") or d.get("slug", "")
    city = d.get("city", "")
    state = d.get("state", "")
    location = ", ".join(x for x in [city, state, "India"] if x)
    return {
        "title": d.get("title", ""),
        "company": "PepsiCo",
        "location": location,
        "url": f"https://www.pepsicojobs.com/main/jobs/{req_id}" if req_id else d.get("apply_url", ""),
        "description": (d.get("description", "") or "")[:500],
        "source": "PepsiCo",
        "search_query": query,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": d.get("posted_date", ""),
    }
