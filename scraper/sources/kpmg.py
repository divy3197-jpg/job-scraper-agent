"""
KPMG India — scrapes the KPMG India careers portal (Oracle Cloud Recruiting CE API).
Method: Public Oracle HCM recruitingCEJobRequisitions REST API (no key).
"""
import time
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
HOST = "https://ejgk.fa.em2.oraclecloud.com"
API_URL = f"{HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
SITE = "CX_1"

QUERIES = [
    "strategy",
    "management consulting",
    "transformation",
    "digital",
    "operations",
    "advisory",
    "business development",
]


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()
    for query in QUERIES:
        for item in _search(query):
            url = item.get("url", "")
            if url and url not in seen and is_relevant(item.get("title", "")):
                seen.add(url)
                results.append(item)
        time.sleep(1)
    return results


def _search(query: str, retries: int = 2) -> list[dict]:
    finder = (
        f'findReqs;siteNumber={SITE},keyword="{query}",'
        f"sortBy=POSTING_DATES_DESC,limit=25"
    )
    params = {
        "onlyData": "true",
        "expand": "requisitionList.secondaryLocations,requisitionList.requisitionFlexFields",
        "finder": finder,
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  [KPMG] HTTP {resp.status_code} for '{query}'")
                return []
            items = resp.json().get("items", [])
            reqs = items[0].get("requisitionList", []) if items else []
            return [_normalise(r, query) for r in reqs]
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(2)
                continue
            print(f"  [KPMG] Error for '{query}': {e}")
            return []
    return []


def _normalise(r: dict, query: str) -> dict:
    req_id = r.get("Id", "")
    title = r.get("Title", "")
    location = r.get("PrimaryLocation", "India")
    # Oracle CE public job URL
    url = (
        f"{HOST}/hcmUI/CandidateExperience/en/sites/{SITE}/job/{req_id}"
        if req_id else ""
    )
    return {
        "title": title,
        "company": "KPMG India",
        "location": location,
        "url": url,
        "description": (r.get("ShortDescriptionStr", "") or "")[:500],
        "source": "KPMG",
        "search_query": query,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": r.get("PostedDate", ""),
    }
