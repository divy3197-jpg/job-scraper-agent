"""Batch AI analysis pipeline — scores jobs against the candidate profile."""
import json
import yaml
from pathlib import Path
from ai.client import generate


def analyse_batch(items: list[dict], context: str = "", preference_prompt: str = "") -> list[dict]:
    """Score and summarise jobs in batches. Drops items below min_score."""
    config = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text())
    ai_cfg = config.get("ai", {})
    model = ai_cfg.get("model", "gemini-2.5-flash")
    rate_limit = float(ai_cfg.get("rate_limit_seconds", 7.0))
    min_score = int(ai_cfg.get("min_score", 0))
    batch_size = int(ai_cfg.get("batch_size", 5))

    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
    print(f"  [AI] {len(items)} jobs → {len(batches)} API calls (batch_size={batch_size})")

    enriched = []
    for i, batch in enumerate(batches):
        print(f"  [AI] Batch {i + 1}/{len(batches)}...", end=" ", flush=True)
        prompt = _build_prompt(batch, context, preference_prompt, config)
        result = generate(prompt, model=model, rate_limit=rate_limit)

        analyses = result.get("analyses", [])
        kept = 0
        for j, item in enumerate(batch):
            ai = analyses[j] if j < len(analyses) else {}
            if not ai:
                enriched.append(item)  # keep without score if AI failed
                kept += 1
                continue

            score = max(0, min(100, int(ai.get("score", 0))))
            if min_score and score < min_score:
                continue

            enriched.append({
                **item,
                "ai_score": score,
                "ai_summary": ai.get("summary", "")[:500],
                "ai_notes": ai.get("notes", "")[:300],
            })
            kept += 1

        print(f"kept {kept}/{len(batch)}")

    return enriched


def _build_prompt(batch: list[dict], context: str, preference_prompt: str, config: dict) -> str:
    priorities = config.get("priorities", [])

    items_text = "\n\n".join(
        f"Job {i + 1}:\n"
        + "\n".join(
            f"  {k}: {v}"
            for k, v in item.items()
            if k not in ("ai_score", "ai_summary", "ai_notes") and v
        )
        for i, item in enumerate(batch)
    )

    return f"""You are a career advisor. Score these {len(batch)} job listings for the candidate below.

# Candidate Profile
{context[:1000] if context else "Not provided"}

# Candidate's Priorities
{chr(10).join(f"- {p}" for p in priorities)}

{preference_prompt}

# Jobs to Analyse
{items_text}

# Task
Return a JSON object with this exact structure:
{{
  "analyses": [
    {{
      "score": <integer 0-100>,
      "summary": "<2-sentence summary of the role and why it fits or doesn't>",
      "notes": "<key match/mismatch: seniority, skills, company tier, location>"
    }}
  ]
}}

Scoring guide: 90-100 = near-perfect match, 70-89 = strong fit, 50-69 = decent fit, 40-49 = marginal, <40 = poor fit.
Return one analysis object per job in the same order. Be concise."""
