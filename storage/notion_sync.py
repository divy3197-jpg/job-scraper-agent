"""Notion storage — deduplicates by URL and pushes new jobs to your database."""
import os
from notion_client import Client
from notion_client.errors import APIResponseError

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise RuntimeError("NOTION_TOKEN not set in environment")
        _client = Client(auth=token)
    return _client


def get_existing_urls(db_id: str) -> set[str]:
    """Fetch all job URLs already in the database (for deduplication)."""
    client, seen, cursor = _get_client(), set(), None
    while True:
        kwargs = {"start_cursor": cursor} if cursor else {}
        resp = client.databases.query(database_id=db_id, page_size=100, **kwargs)
        for page in resp.get("results", []):
            url = page.get("properties", {}).get("URL", {}).get("url") or ""
            if url:
                seen.add(url)
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return seen


def push_job(db_id: str, job: dict) -> bool:
    """Push a single job to Notion. Returns True on success."""
    props = {
        "Name": {
            "title": [{"text": {"content": job.get("title", "")[:100]}}]
        },
        "URL": {"url": job.get("url") or ""},
        "Company": {
            "rich_text": [{"text": {"content": job.get("company", "")[:200]}}]
        },
        "Location": {
            "rich_text": [{"text": {"content": job.get("location", "")[:200]}}]
        },
        "Source": {
            "select": {"name": job.get("source", "Unknown")}
        },
        "Search Query": {
            "rich_text": [{"text": {"content": job.get("search_query", "")[:100]}}]
        },
        "Date Found": {
            "date": {"start": job.get("date_found", "")}
        },
        "Status": {
            "select": {"name": "New"}
        },
    }

    if job.get("posted_date"):
        props["Posted Date"] = {
            "rich_text": [{"text": {"content": str(job["posted_date"])[:100]}}]
        }

    if job.get("ai_score") is not None:
        props["AI Score"] = {"number": job["ai_score"]}

    if job.get("ai_summary"):
        props["AI Summary"] = {
            "rich_text": [{"text": {"content": job["ai_summary"][:2000]}}]
        }

    if job.get("ai_notes"):
        props["AI Notes"] = {
            "rich_text": [{"text": {"content": job["ai_notes"][:2000]}}]
        }

    if job.get("description"):
        props["Description"] = {
            "rich_text": [{"text": {"content": job["description"][:2000]}}]
        }

    try:
        _get_client().pages.create(
            parent={"database_id": db_id},
            properties=props,
        )
        return True
    except APIResponseError as e:
        print(f"  [Notion] Push failed for '{job.get('title', '')}': {e}")
        return False


def sync(db_id: str, jobs: list[dict]) -> tuple[int, int]:
    """Sync a list of jobs to Notion. Returns (added, skipped)."""
    existing = get_existing_urls(db_id)
    added = skipped = 0

    for job in jobs:
        url = job.get("url", "")
        if url and url in existing:
            skipped += 1
            continue
        if push_job(db_id, job):
            added += 1
            if url:
                existing.add(url)
        else:
            skipped += 1

    return added, skipped
