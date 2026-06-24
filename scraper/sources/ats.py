"""
Generic ATS connectors — pull jobs from many companies via their hiring platforms
(Workday, Greenhouse, Lever). Companies are listed in companies.py.

Each connector filters to India-based (or India-remote) roles and to titles relevant
to an MBA strategy/consulting/growth/product profile before returning.
"""
import time
import requests
from datetime import datetime, timezone
from scraper.sources.companies import WORKDAY, GREENHOUSE, LEVER

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
HJ = {**UA, "Content-Type": "application/json", "Accept": "application/json"}

INDIA_CITIES = ("india", "bangalore", "bengaluru", "mumbai", "hyderabad", "gurgaon",
                "gurugram", "delhi", "noida", "pune", "chennai", "kolkata", "ahmedabad")

# Titles worth surfacing for an MBA strategy/growth/consulting/product candidate
RELEVANT = ("strateg", "consult", "growth", "product manager", "product management",
            "business development", "go-to-market", "gtm", "transformation", "category",
            "marketing", "operations manager", "chief of staff", "founder", "principal product",
            "business analyst", "program manager", "commercial", "advisory", "corporate development",
            "business operations", "biz ops", "revenue", "partnerships", "manager - strategy")

EXCLUDE = ("software engineer", "sde", "data engineer", "devops", "frontend", "backend",
           "full stack", "qa engineer", "sdet", "security engineer", "network engineer",
           "android", "ios developer", "machine learning engineer", "site reliability",
           "hardware", "firmware", "support engineer", "technician", "warehouse", "driver")


def _india(text: str) -> bool:
    t = (text or "").lower()
    return any(c in t for c in INDIA_CITIES)


def _relevant(title: str) -> bool:
    t = (title or "").lower()
    if any(x in t for x in EXCLUDE):
        return False
    return any(k in t for k in RELEVANT)


def _row(title, company, location, url, desc, source_tag):
    return {
        "title": title, "company": company, "location": location or "India",
        "url": url, "description": (desc or "")[:400], "source": source_tag,
        "search_query": "ATS", "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": "",
    }


def _workday(name, tenant, site, dc):
    base = f"https://{tenant}.{dc}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    out = []
    for kw in ("strategy", "consulting", "growth", "product manager"):
        try:
            r = requests.post(url, json={"limit": 20, "offset": 0, "searchText": kw, "appliedFacets": {}},
                              headers=HJ, timeout=15)
            if r.status_code != 200:
                continue
            for j in r.json().get("jobPostings", []):
                loc = j.get("locationsText", "")
                if not _india(loc) or not _relevant(j.get("title", "")):
                    continue
                ext = j.get("externalPath", "")
                out.append(_row(j.get("title", ""), name, loc, f"{base}/{site}{ext}", "", name))
            time.sleep(0.4)
        except requests.RequestException:
            continue
    return out


def _greenhouse(name, token):
    out = []
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                         headers=UA, timeout=15)
        if r.status_code != 200:
            return out
        for j in r.json().get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            if not _india(loc) or not _relevant(j.get("title", "")):
                continue
            out.append(_row(j.get("title", ""), name, loc, j.get("absolute_url", ""), "", name))
    except requests.RequestException:
        pass
    return out


def _lever(name, token):
    out = []
    try:
        r = requests.get(f"https://api.lever.co/v0/postings/{token}?mode=json",
                         headers=UA, timeout=15)
        if r.status_code != 200:
            return out
        for j in r.json():
            cats = j.get("categories", {}) or {}
            loc = cats.get("location", "")
            if not _india(loc) or not _relevant(j.get("text", "")):
                continue
            out.append(_row(j.get("text", ""), name, loc, j.get("hostedUrl", ""),
                            (j.get("descriptionPlain", "") or "")[:400], name))
    except requests.RequestException:
        pass
    return out


def fetch(days: int = 7) -> list[dict]:
    results, seen = [], set()

    def add(rows):
        for r in rows:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u)
                results.append(r)

    for name, tenant, site, dc in WORKDAY:
        add(_workday(name, tenant, site, dc))
    for name, token in GREENHOUSE:
        add(_greenhouse(name, token))
    for name, token in LEVER:
        add(_lever(name, token))

    return results
