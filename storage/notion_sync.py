"""Notion storage — deduplicates by URL and pushes new jobs to your database."""
import os
import time
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError, HTTPResponseError

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            raise RuntimeError("NOTION_TOKEN not set in environment")
        _client = Client(auth=token)
    return _client


def get_existing_keys(db_id: str) -> tuple[set[str], set[tuple[str, str]]]:
    """Fetch existing job URLs and (title, company) keys for deduplication."""
    client, urls, keys, cursor = _get_client(), set(), set(), None
    while True:
        kwargs = {"start_cursor": cursor} if cursor else {}
        resp = None
        for attempt in range(3):
            try:
                resp = client.databases.query(database_id=db_id, page_size=100, **kwargs)
                break
            except (RequestTimeoutError, HTTPResponseError) as e:
                if attempt == 2:
                    print(f"  [Notion] Query failed after retries: {e}")
                    return urls, keys  # return what we have; sync still proceeds
                time.sleep(2 * (attempt + 1))
        for page in resp.get("results", []):
            props = page.get("properties", {})
            url = props.get("URL", {}).get("url") or ""
            if url:
                urls.add(url)
            title_arr = props.get("Name", {}).get("title", [])
            comp_arr = props.get("Company", {}).get("rich_text", [])
            title = title_arr[0]["text"]["content"] if title_arr else ""
            company = comp_arr[0]["text"]["content"] if comp_arr else ""
            if title:
                keys.add((title.strip().lower(), company.strip().lower()))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return urls, keys


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

    for attempt in range(3):
        try:
            _get_client().pages.create(
                parent={"database_id": db_id},
                properties=props,
            )
            return True
        except RequestTimeoutError:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))  # transient — retry
                continue
            print(f"  [Notion] Timeout pushing '{job.get('title', '')}' — skipping")
            return False
        except APIResponseError as e:
            print(f"  [Notion] Push failed for '{job.get('title', '')}': {e}")
            return False
    return False


def sync(db_id: str, jobs: list[dict]) -> tuple[int, int]:
    """Sync a list of jobs to Notion. Returns (added, skipped)."""
    existing_urls, existing_keys = get_existing_keys(db_id)
    added = skipped = 0

    for job in jobs:
        url = job.get("url", "")
        key = (job.get("title", "").strip().lower(), job.get("company", "").strip().lower())
        if (url and url in existing_urls) or (key[0] and key in existing_keys):
            skipped += 1
            continue
        if push_job(db_id, job):
            added += 1
            if url:
                existing_urls.add(url)
            if key[0]:
                existing_keys.add(key)
        else:
            skipped += 1

    return added, skipped
