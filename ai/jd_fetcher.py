"""Fetch the full job description text from a job posting URL (LinkedIn-aware)."""
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_jd(url: str) -> dict:
    """
    Returns {"description": str, "criteria": list[str]} for a job URL.
    Falls back to empty fields if the page can't be parsed.
    """
    out = {"description": "", "criteria": []}
    if not url:
        return out
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return out
        soup = BeautifulSoup(resp.text, "lxml")

        desc = soup.select_one(".show-more-less-html__markup, .description__text")
        if desc:
            out["description"] = desc.get_text("\n", strip=True)

        for c in soup.select(".description__job-criteria-item"):
            out["criteria"].append(" ".join(c.get_text(" ", strip=True).split()))
    except requests.RequestException:
        pass
    return out
