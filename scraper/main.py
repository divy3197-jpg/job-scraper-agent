"""Orchestrator: scrape → deduplicate → AI enrich → store in Notion."""
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from scraper.sources import adzuna, linkedin, naukri
from storage.notion_sync import sync


def ai_enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def main():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text())

    db_id = os.environ.get("NOTION_DATABASE_ID")
    if not db_id:
        print("ERROR: NOTION_DATABASE_ID not set in environment")
        sys.exit(1)

    queries = config["search"]["queries"]
    locations = config["search"]["locations"]
    days = config["search"].get("date_range_days", 7)

    # --- Scrape all sources ---
    all_items: list[dict] = []

    print(f"\n[Adzuna] Fetching...")
    try:
        items = adzuna.fetch(days)
        print(f"  → {len(items)} items")
        all_items.extend(items)
    except Exception as e:
        print(f"  [Adzuna] FAILED: {e}")

    print(f"\n[LinkedIn] Fetching...")
    try:
        items = linkedin.fetch(queries, locations, days)
        print(f"  → {len(items)} items")
        all_items.extend(items)
    except Exception as e:
        print(f"  [LinkedIn] FAILED: {e}")

    print(f"\n[Naukri] Fetching...")
    try:
        items = naukri.fetch(days)
        print(f"  → {len(items)} items")
        all_items.extend(items)
    except Exception as e:
        print(f"  [Naukri] FAILED: {e}")

    # --- Deduplicate by URL ---
    seen, deduped = set(), []
    for item in all_items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(item)

    print(f"\nTotal unique jobs: {len(deduped)}")

    # --- AI Enrichment ---
    if ai_enabled() and deduped:
        from ai.memory import load_feedback, build_preference_prompt
        from ai.pipeline import analyse_batch

        feedback = load_feedback()
        preference = build_preference_prompt(feedback)
        context_path = Path(__file__).parent.parent / "profile" / "context.md"
        context = context_path.read_text() if context_path.exists() else ""

        print(f"\n[AI] Scoring {len(deduped)} jobs...")
        deduped = analyse_batch(deduped, context=context, preference_prompt=preference)
        print(f"  → {len(deduped)} jobs passed minimum score threshold")
    else:
        if not ai_enabled():
            print("\n[AI] Skipped — GEMINI_API_KEY not set")

    # --- Store in Notion ---
    print(f"\n[Notion] Syncing {len(deduped)} jobs...")
    added, skipped = sync(db_id, deduped)
    print(f"  → {added} new jobs added, {skipped} already existed\n")


if __name__ == "__main__":
    main()
