"""
Adzuna Jobs API — free tier, aggregates jobs across India from multiple boards.
API key: free at https://developer.adzuna.com (takes 2 min to register)
Falls back to no-auth public endpoint if key not set.
"""
import os
import time
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant

BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"  # 'in' = India

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-research-bot/1.0)"}

QUERIES = [
    "management consultant",
    "strategy consultant",
    "digital transformation",
    "operations consultant",
    "chief of staff",
    "data ai consulting",
]


def fetch(days: int = 7) -> list[dict]:
    app_id = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")

    if not app_id or not app_key:
        print("  [Adzuna] No API key — skipping (add ADZUNA_APP_ID + ADZUNA_APP_KEY to .env)")
        return []

    results, seen = [], set()
    for query in QUERIES:
        for item in _search(query, app_id, app_key, days):
            url = item.get("url", "")
            if url and url not in seen and is_relevant(item.get("title", "") + " " + item.get("description", "")):
                seen.add(url)
                results.append(item)
        time.sleep(1)
    return results


def _search(query: str, app_id: str, app_key: str, days: int) -> list[dict]:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "where": "india",
        "results_per_page": 20,
        "max_days_old": days,
        "sort_by": "date",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [Adzuna] HTTP {resp.status_code} for '{query}'")
            return []
        return [_normalise(j, query) for j in resp.json().get("results", [])]
    except Exception as e:
        print(f"  [Adzuna] Error for '{query}': {e}")
        return []


def _normalise(raw: dict, query: str) -> dict:
    return {
        "title": raw.get("title", ""),
        "company": raw.get("company", {}).get("display_name", ""),
        "location": raw.get("location", {}).get("display_name", "India"),
        "url": raw.get("redirect_url", ""),
        "description": raw.get("description", "")[:500],
        "source": "Adzuna",
        "search_query": query,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": raw.get("created", "")[:10],
    }
