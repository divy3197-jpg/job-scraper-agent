"""
One-time setup: creates the Notion database with the correct schema.
Run once before first scrape: python setup.py
"""
import os
import sys
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def create_database(client: Client, parent_page_id: str) -> str:
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Job Leads — Divy Kumar Sinha"}}],
        properties={
            "Name": {"title": {}},
            "URL": {"url": {}},
            "Company": {"rich_text": {}},
            "Location": {"rich_text": {}},
            "Source": {
                "select": {
                    "options": [
                        {"name": "Indeed", "color": "blue"},
                        {"name": "LinkedIn", "color": "green"},
                        {"name": "IIMJobs", "color": "orange"},
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "New", "color": "gray"},
                        {"name": "Saved", "color": "blue"},
                        {"name": "Applied", "color": "green"},
                        {"name": "Interested", "color": "yellow"},
                        {"name": "Strong Match", "color": "purple"},
                        {"name": "Skip", "color": "red"},
                        {"name": "Rejected", "color": "red"},
                        {"name": "Not Relevant", "color": "red"},
                        {"name": "Too Senior", "color": "pink"},
                        {"name": "Too Junior", "color": "pink"},
                    ]
                }
            },
            "AI Score": {"number": {"format": "number"}},
            "AI Summary": {"rich_text": {}},
            "AI Notes": {"rich_text": {}},
            "Description": {"rich_text": {}},
            "Search Query": {"rich_text": {}},
            "Posted Date": {"rich_text": {}},
            "Date Found": {"date": {}},
        },
    )
    return db["id"]


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("ERROR: NOTION_TOKEN not set in .env")
        sys.exit(1)

    client = Client(auth=token)

    print("Paste the ID of the Notion page where the database should be created.")
    print("(Open the page in Notion → Copy link → the ID is the last 32-char segment)")
    page_id = input("Parent page ID: ").strip().replace("-", "")

    if len(page_id) != 32:
        print(f"ERROR: Expected 32-character ID, got {len(page_id)} characters")
        sys.exit(1)

    print("\nCreating Notion database...")
    db_id = create_database(client, page_id)
    print(f"\n✓ Database created!")
    print(f"\nAdd this to your .env file:")
    print(f"  NOTION_DATABASE_ID={db_id}")
    print(f"\nAnd add it as a GitHub Secret named NOTION_DATABASE_ID")


if __name__ == "__main__":
    main()
