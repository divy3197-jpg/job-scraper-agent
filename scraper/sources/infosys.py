"""
Infosys — scrapes the Infosys experienced-hire careers portal.
Method: Public JSON API (getCareerSearchJobs) behind career.infosys.com.
Filters to India + genuine strategy/consulting/business titles (not the generic
"Consultant" band that Infosys attaches to technical roles).
"""
import requests
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://career.infosys.com",
    "Referer": "https://career.infosys.com/",
}
API = "https://intapgateway.infosysapps.com/careersci/search/intapjbsrch/getCareerSearchJobs"

# Genuine business/strategy/consulting titles (matched on the posting TITLE, not band)
KEEP = ("strateg", "management consult", "business consult", "digital transformation",
        "business analyst", "product manager", "growth", "go-to-market", "gtm",
        "transformation lead", "transformation manager", "advisory", "business development",
        "domain consultant", "functional consultant", "process consultant", "industry consult",
        "operations consult", "value", "pre-sales", "presales", "client partner")
# Technical roles to exclude even if "consultant" appears in band/title
DROP = ("developer", "engineer", "sde", "architect", "administrator", "tester", "qa ",
        "java", "python", "react", "angular", ".net", "sap ", "devops", "etl", "gis ",
        "full stack", "frontend", "backend", "data engineer", "ml ", "cloud ops",
        "network", "security analyst", "support", "lead developer")


def fetch(days: int = 7) -> list[dict]:
    try:
        r = requests.get(API, params={"sourceId": "1,21", "searchText": "ALL"},
                         headers=HEADERS, timeout=25)
        if r.status_code != 200:
            print(f"  [Infosys] HTTP {r.status_code}")
            return []
        data = r.json()
    except Exception as e:
        print(f"  [Infosys] Error: {e}")
        return []

    results, seen = [], set()
    for j in data:
        if "india" not in str(j.get("country", "")).lower():
            continue
        title = j.get("postingTitle", "")
        t = title.lower()
        if any(d in t for d in DROP):
            continue
        if not any(k in t for k in KEEP):
            continue
        ref = j.get("referenceCode", "")
        if not ref or ref in seen:
            continue
        seen.add(ref)
        results.append(_normalise(j, ref))
    return results


def _normalise(j: dict, ref: str) -> dict:
    loc = (j.get("location", "") or "").title()
    yoe = f"{j.get('minExperienceLevel', '')}-{j.get('maxExperienceLevel', '')}y"
    desc = f"[{j.get('roleDesignation', '')} | {yoe} | {j.get('unit', '')}] " + (j.get("postingDescription", "") or "")
    return {
        "title": j.get("postingTitle", ""),
        "company": "Infosys",
        "location": f"{loc}, India" if loc else "India",
        "url": f"https://career.infosys.com/jobdesc?jobReferenceCode={ref}&search=true",
        "description": desc[:500],
        "source": "Infosys",
        "search_query": "strategy/consulting",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "posted_date": (j.get("createdOn", "") or "")[:10],
    }
