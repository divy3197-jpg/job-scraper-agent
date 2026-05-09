"""
Naukri.com — scrapes India's largest job board via their JSON API.
Method: Unofficial search API endpoint (same one their frontend uses)
"""
import time
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "systemid": "Naukri",
    "appid": "109",
}

API_URL = "https://www.naukri.com/jobapi/v3/search"

QUERIES = [
    "management consultant",
    "strategy consultant",
    "digital transformation",
    "operations consultant",
    "chief of staff",
    "consulting associate",
    "business development consulting",
]


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()
    for query in QUERIES:
        for item in _search(query):
            url = item.get("url", "")
            if url and url not in seen and is_relevant(item.get("title", "") + " " + item.get("description", "")):
                seen.add(url)
                results.append(item)
        time.sleep(1.5)
    return results


def _search(query: str) -> list[dict]:
    params = {
        "noOfResults": 20,
        "urlType": "search_by_keyword",
        "searchType": "adv",
        "keyword": query,
        "location": "india",
        "experience": "2",
        "sort": "1",  # sort by date
        "pageNo": 1,
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [Naukri] HTTP {resp.status_code} for '{query}'")
            return []
        data = resp.json()
        return [_normalise(j, query) for j in data.get("jobDetails", [])]
    except Exception as e:
        print(f"  [Naukri] Error for '{query}': {e}")
        return []


def _normalise(raw: dict, query: str) -> dict:
    title = raw.get("title", "")
    company = raw.get("companyName", "")
    job_id = raw.get("jobId", "")
    url = f"https://www.naukri.com/{raw.get('staticUrl', '')}" if raw.get("staticUrl") else f"https://www.naukri.com/job-listings-{job_id}"
    location = ", ".join(raw.get("placeholders", [{}])[0].get("label", "India").split(",")[:2]) if raw.get("placeholders") else "India"
    description = raw.get("jobDescription", "")[:500]

    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "description": description,
        "source": "Naukri",
        "search_query": query,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": raw.get("modifiedOn", ""),
    }
