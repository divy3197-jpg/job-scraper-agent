"""Feedback learning — reads your Notion decisions to bias future AI scoring."""
import json
from pathlib import Path

FEEDBACK_PATH = Path(__file__).parent.parent / "data" / "feedback.json"


def load_feedback() -> dict:
    if FEEDBACK_PATH.exists():
        try:
            return json.loads(FEEDBACK_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"positive": [], "negative": []}


def save_feedback(fb: dict):
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(fb, indent=2, ensure_ascii=False))


def build_preference_prompt(feedback: dict, max_examples: int = 15) -> str:
    """Convert feedback history into a scoring bias section for the AI prompt."""
    lines = []

    if feedback.get("positive"):
        lines.append("# Jobs this candidate LIKED / applied to (positive signal):")
        for e in feedback["positive"][-max_examples:]:
            lines.append(f"  - {e}")

    if feedback.get("negative"):
        lines.append("\n# Jobs this candidate SKIPPED / rejected (negative signal):")
        for e in feedback["negative"][-max_examples:]:
            lines.append(f"  - {e}")

    if lines:
        lines.append("\nBias your scoring toward the positive patterns and away from the negative ones.")

    return "\n".join(lines)


def sync_from_notion(notion_client, db_id: str, positive_statuses: list, negative_statuses: list):
    """
    Pull decisions from Notion and update feedback.json.
    Call this from a separate feedback_sync.py after reviewing jobs in Notion.
    """
    fb = {"positive": [], "negative": []}

    def query_status(statuses):
        results = []
        for status in statuses:
            resp = notion_client.databases.query(
                database_id=db_id,
                filter={"property": "Status", "select": {"equals": status}},
                page_size=100,
            )
            for page in resp.get("results", []):
                props = page.get("properties", {})
                title = props.get("Name", {}).get("title", [{}])
                company = props.get("Company", {}).get("rich_text", [{}])
                name = title[0].get("text", {}).get("content", "") if title else ""
                co = company[0].get("text", {}).get("content", "") if company else ""
                if name:
                    results.append(f"{name} at {co}" if co else name)
        return results

    fb["positive"] = query_status(positive_statuses)
    fb["negative"] = query_status(negative_statuses)
    save_feedback(fb)
    print(f"[Feedback] Saved {len(fb['positive'])} positive, {len(fb['negative'])} negative signals")
