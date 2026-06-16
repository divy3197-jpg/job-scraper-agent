"""
Generate tailored cover letters for your top job matches.

Pulls the highest-scored jobs from Notion that don't yet have a cover letter,
fetches each full job description, generates a tailored letter with Gemini,
saves it to applications/, and writes it into the Notion page + ticks the
"Cover Letter" checkbox.

Usage:
    python generate_cover_letters.py            # top 5 jobs scoring >= min_score
    python generate_cover_letters.py --count 10 # top 10
    python generate_cover_letters.py --min 90   # only jobs scoring >= 90
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from notion_client import Client
from ai.jd_fetcher import fetch_jd
from ai.cover_letter import generate_cover_letter

APP_DIR = Path(__file__).parent / "applications"
CONTACT = (
    "Divy Kumar Sinha\n"
    "Hyderabad, India | +91-7677883722 | divyk2024@email.iimcal.ac.in | "
    "linkedin.com/in/divy-sinha"
)


def _txt(props, field):
    arr = props.get(field, {}).get("rich_text", [])
    return arr[0]["text"]["content"] if arr else ""


def fetch_candidates(client, db_id, min_score, count):
    """Top-scored jobs without a cover letter, not rejected."""
    jobs, cursor = [], None
    while True:
        kwargs = {"start_cursor": cursor} if cursor else {}
        resp = client.databases.query(
            database_id=db_id, page_size=100,
            sorts=[{"property": "AI Score", "direction": "descending"}], **kwargs,
        )
        for p in resp["results"]:
            pr = p["properties"]
            score = pr.get("AI Score", {}).get("number")
            has_letter = pr.get("Cover Letter", {}).get("checkbox", False)
            status = (pr.get("Status", {}).get("select") or {}).get("name", "New")
            if score is None or score < min_score or has_letter:
                continue
            if status in ("Skip", "Rejected", "Not Relevant", "Too Senior", "Too Junior"):
                continue
            title = pr.get("Name", {}).get("title", [])
            jobs.append({
                "page_id": p["id"],
                "title": title[0]["text"]["content"] if title else "",
                "company": _txt(pr, "Company"),
                "location": _txt(pr, "Location"),
                "url": pr.get("URL", {}).get("url", ""),
                "score": score,
            })
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return jobs[:count]


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:60]


def save_to_file(job, letter):
    APP_DIR.mkdir(exist_ok=True)
    fname = f"{_slug(job['company'])}_{_slug(job['title'])}.md"
    path = APP_DIR / fname
    content = (
        f"# Cover Letter — {job['title']} ({job['company']})\n\n"
        f"**{CONTACT}**\n\n"
        f"> Job: {job['url']}  |  AI Score: {int(job['score'])}\n\n---\n\n"
        f"{letter}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def write_to_notion(client, page_id, letter):
    """Tick the checkbox and (re)write the letter as page content."""
    client.pages.update(page_id=page_id, properties={"Cover Letter": {"checkbox": True}})
    # Clear any previously written blocks so re-runs replace instead of duplicate.
    try:
        existing = client.blocks.children.list(block_id=page_id, page_size=100)
        for b in existing.get("results", []):
            client.blocks.delete(block_id=b["id"])
    except Exception:
        pass
    # Notion blocks cap at 2000 chars each — chunk the letter into paragraphs.
    blocks = [{
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Cover Letter"}}]},
    }]
    for para in [p for p in letter.split("\n") if p.strip()]:
        blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": para[:2000]}}]},
        })
    client.blocks.children.append(block_id=page_id, children=blocks[:100])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5, help="how many letters to generate")
    ap.add_argument("--min", type=int, default=85, help="minimum AI score")
    args = ap.parse_args()

    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not db_id:
        print("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")
        sys.exit(1)
    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY must be set in .env")
        sys.exit(1)

    client = Client(auth=token)
    context_path = Path(__file__).parent / "profile" / "context.md"
    context = context_path.read_text(encoding="utf-8") if context_path.exists() else ""

    jobs = fetch_candidates(client, db_id, args.min, args.count)
    if not jobs:
        print(f"No jobs scoring >= {args.min} without a cover letter. Nothing to do.")
        return

    print(f"Generating cover letters for {len(jobs)} jobs (score >= {args.min})...\n")
    for i, job in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] [{int(job['score'])}] {job['title']} @ {job['company']}")
        jd = fetch_jd(job["url"])
        letter = generate_cover_letter(job, jd.get("description", ""), context)
        if not letter:
            print("    ! Generation failed (likely Gemini quota) — skipping")
            continue
        path = save_to_file(job, letter)
        try:
            write_to_notion(client, job["page_id"], letter)
            print(f"    ✓ Saved {path.name} + written to Notion")
        except Exception as e:
            print(f"    ✓ Saved {path.name} (Notion write failed: {e})")
        time.sleep(2)

    print(f"\nDone. Letters are in: {APP_DIR}")


if __name__ == "__main__":
    main()
