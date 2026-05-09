"""
IIMJobs — scrapes MBA-focused job listings from iimjobs.com.
Method: HTML scraping (India's premier MBA job board)
"""
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

# IIMJobs URL-slug → display name
SEARCH_SLUGS = {
    "management-consulting": "management consultant",
    "strategy": "strategy consultant",
    "digital-transformation": "digital transformation",
    "operations": "operations consultant",
    "chief-of-staff": "chief of staff",
    "business-development": "business development",
}


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()
    for slug, display in SEARCH_SLUGS.items():
        for item in _fetch_slug(slug, display):
            url = item.get("url", "")
            if url and url not in seen:
                if is_relevant(item.get("title", "") + " " + item.get("description", "")):
                    seen.add(url)
                    results.append(item)
        time.sleep(2)
    return results


def _fetch_slug(slug: str, display: str) -> list[dict]:
    url = f"https://www.iimjobs.com/j/{slug}-jobs-1.html"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [IIMJobs] HTTP {resp.status_code} for '{slug}'")
            return []
        return _parse(resp.text, display)
    except requests.RequestException as e:
        print(f"  [IIMJobs] Request error: {e}")
        return []


def _parse(html: str, query: str) -> list[dict]:
    items = []
    soup = BeautifulSoup(html, "lxml")

    # IIMJobs uses multiple possible selectors across site versions
    cards = soup.select(".job-wrap") or soup.select(".jobs-list .job") or soup.select("article.job")

    for card in cards:
        title_el = card.select_one("h2 a, h3 a, .job-title a")
        company_el = card.select_one(".company-name, .job-company, .company")
        location_el = card.select_one(".location, .job-location, .loc")
        desc_el = card.select_one(".description, .job-desc, p.desc")

        if not title_el:
            continue

        href = title_el.get("href", "")
        if not href.startswith("http"):
            href = f"https://www.iimjobs.com{href}"

        items.append({
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else "",
            "location": location_el.get_text(strip=True) if location_el else "India",
            "url": href,
            "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
            "source": "IIMJobs",
            "search_query": query,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "posted_date": "",
        })

    return items
