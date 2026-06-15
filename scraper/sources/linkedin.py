"""
LinkedIn Jobs — scrapes listings via LinkedIn's guest job search endpoint.
Method: Unofficial guest JSON/HTML endpoint (no login required)
Rate-limited with sleep between requests to avoid blocks.
"""
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

# LinkedIn time filter mapping
_TPR = {1: "r86400", 3: "r259200", 7: "r604800", 14: "r1209600", 30: "r2592000"}


def fetch(queries: list[str], locations: list[str], days: int = 7) -> list[dict]:
    results, seen = [], set()
    f_tpr = _TPR.get(days, "r604800")

    # Cover more queries/locations and paginate 2 pages each for broader reach.
    combos = [(q, l) for q in queries[:6] for l in locations[:3]]
    for query, location in combos:
        for start in (0, 25):
            for item in _fetch_jobs(query, location, f_tpr, start):
                url = item.get("url", "")
                if url and url not in seen and is_relevant(item.get("title", "")):
                    seen.add(url)
                    results.append(item)
            time.sleep(2)

    return results


def _fetch_jobs(query: str, location: str, f_tpr: str, start: int = 0) -> list[dict]:
    params = {"keywords": query, "location": location, "f_TPR": f_tpr, "start": start}
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 429:
            print("  [LinkedIn] Rate limited — skipping")
            return []
        if resp.status_code != 200:
            print(f"  [LinkedIn] HTTP {resp.status_code} for '{query}'")
            return []
        return _parse_html(resp.text, query)
    except requests.RequestException as e:
        print(f"  [LinkedIn] Request error: {e}")
        return []


def _parse_html(html: str, query: str) -> list[dict]:
    items = []
    soup = BeautifulSoup(html, "lxml")

    for card in soup.select("li"):
        title_el = card.select_one(".base-search-card__title, h3.base-search-card__title")
        company_el = card.select_one(".base-search-card__subtitle")
        location_el = card.select_one(".job-search-card__location")
        link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
        date_el = card.select_one("time")

        if not title_el or not link_el:
            continue

        url = link_el.get("href", "").split("?")[0]
        if not url.startswith("http"):
            url = f"https://www.linkedin.com{url}"

        items.append({
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "url": url,
            "description": "",
            "source": "LinkedIn",
            "search_query": query,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "posted_date": date_el.get("datetime", "") if date_el else "",
        })

    return items
