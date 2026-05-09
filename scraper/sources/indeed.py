"""
Indeed Jobs — scrapes listings via Indeed's public RSS feed.
Method: RSS/XML (no API key, no authentication)
"""
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-research-bot/1.0)"}
# India Indeed uses a regional subdomain
RSS_URLS = [
    "https://in.indeed.com/rss",
    "https://www.indeed.com/rss",
]


def fetch(queries: list[str], locations: list[str], days: int = 7) -> list[dict]:
    results, seen = [], set()
    for query in queries:
        for location in locations:
            for item in _fetch_feed(query, location, days):
                url = item.get("url", "")
                if url and url not in seen:
                    text = item.get("title", "") + " " + item.get("description", "")
                    if is_relevant(text):
                        seen.add(url)
                        results.append(item)
            time.sleep(1)
    return results


def _fetch_feed(query: str, location: str, days: int) -> list[dict]:
    params = {"q": query, "l": location, "sort": "date", "fromage": str(days)}
    for base_url in RSS_URLS:
        try:
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return _parse_rss(resp.text, query)
        except requests.RequestException:
            continue
    print(f"  [Indeed] All URLs failed for '{query}' in '{location}'")
    return []


def _parse_rss(xml_text: str, query: str) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  [Indeed] XML parse error: {e}")
        return items

    for node in root.findall(".//item"):
        raw_title = node.findtext("title", "").strip()
        link = node.findtext("link", "").strip()
        description = node.findtext("description", "").strip()
        pub_date = node.findtext("pubDate", "").strip()

        # Indeed title format: "Job Title - Company Name"
        title, company = raw_title, ""
        if " - " in raw_title:
            parts = raw_title.rsplit(" - ", 1)
            title, company = parts[0].strip(), parts[1].strip()

        items.append({
            "title": title,
            "company": company,
            "location": "",
            "url": link,
            "description": description[:600],
            "source": "Indeed",
            "search_query": query,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "posted_date": pub_date,
        })

    return items
