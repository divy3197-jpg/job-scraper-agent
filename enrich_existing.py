"""
Backfill AI scores on existing Notion rows that have no AI Score.
Run manually when needed: python enrich_existing.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def fetch_unscored(client: Client, db_id: str) -> list[dict]:
    results, cursor = [], None
    while True:
        kwargs = {"start_cursor": cursor} if cursor else {}
        resp = client.databases.query(
            database_id=db_id,
            filter={"property": "AI Score", "number": {"is_empty": True}},
            page_size=100,
            **kwargs,
        )
        for page in resp.get("results", []):
            props = page.get("properties", {})
            title_arr = props.get("Name", {}).get("title", [])
            company_arr = props.get("Company", {}).get("rich_text", [])
            desc_arr = props.get("Description", {}).get("rich_text", [])
            loc_arr = props.get("Location", {}).get("rich_text", [])
            source_sel = props.get("Source", {}).get("select") or {}

            results.append({
                "_page_id": page["id"],
                "title": title_arr[0]["text"]["content"] if title_arr else "",
                "company": company_arr[0]["text"]["content"] if company_arr else "",
                "location": loc_arr[0]["text"]["content"] if loc_arr else "",
                "description": desc_arr[0]["text"]["content"] if desc_arr else "",
                "source": source_sel.get("name", ""),
            })

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    return results


def update_page(client: Client, page_id: str, score: int, summary: str, notes: str):
    client.pages.update(
        page_id=page_id,
        properties={
            "AI Score": {"number": score},
            "AI Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]},
            "AI Notes": {"rich_text": [{"text": {"content": notes[:2000]}}]},
        },
    )


def main():
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not db_id:
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID must be set")
        sys.exit(1)

    client = Client(auth=token)

    print("Fetching unscored jobs from Notion...")
    jobs = fetch_unscored(client, db_id)
    print(f"Found {len(jobs)} unscored jobs")

    if not jobs:
        print("Nothing to enrich.")
        return

    from ai.memory import load_feedback, build_preference_prompt
    from ai.pipeline import analyse_batch

    context_path = Path(__file__).parent / "profile" / "context.md"
    context = context_path.read_text() if context_path.exists() else ""
    feedback = load_feedback()
    preference = build_preference_prompt(feedback)

    enriched = analyse_batch(jobs, context=context, preference_prompt=preference)

    updated = 0
    for item in enriched:
        page_id = item.get("_page_id")
        if not page_id or item.get("ai_score") is None:
            continue
        update_page(client, page_id, item["ai_score"], item.get("ai_summary", ""), item.get("ai_notes", ""))
        updated += 1

    print(f"Updated {updated} jobs with AI scores")


if __name__ == "__main__":
    main()
