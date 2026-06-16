# Job Scraper Agent — Divy Kumar Sinha

Automatically scrapes job listings from **Indeed, LinkedIn, and IIMJobs** daily, scores each role against your CV using **Gemini AI**, and pushes matching jobs into a **Notion database**. Runs free on GitHub Actions.

## What it does

1. Searches for consulting, strategy, digital transformation, and related roles across 3 job boards
2. Filters out irrelevant listings (interns, freshers, etc.) before calling the AI
3. Scores each job 0–100 using Gemini Flash with your CV as context
4. Drops jobs below score 40, pushes the rest to Notion with AI summary + notes
5. Learns from your Notion decisions (Saved/Applied vs Skip/Rejected) to improve scoring over time
6. Runs daily at 8 AM IST via GitHub Actions — completely free

---

## Setup (5 minutes)

### 1. Prerequisites
- Python 3.11+
- A [Notion account](https://notion.so) (free)
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free, 500 req/day)
- A [GitHub account](https://github.com) (for free CI/CD)

### 2. Create a Notion Integration
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration** → name it "Job Scraper"
3. Copy the **Internal Integration Token** → this is your `NOTION_TOKEN`

### 3. Set up local environment
```bash
cd job-scraper-agent
pip install -r requirements.txt
cp .env.example .env
# Fill in NOTION_TOKEN and GEMINI_API_KEY in .env
```

### 4. Create the Notion database
```bash
python setup.py
# Follow the prompt — paste your Notion parent page ID
# It prints your NOTION_DATABASE_ID — add it to .env
```

**To find your parent page ID:** Open Notion → go to the page where you want the jobs database → Copy link → the ID is the last 32 characters before any `?`.

**Important:** Share the integration with your page: open the page in Notion → click `...` → **Add connections** → select "Job Scraper".

### 5. Test locally
```bash
python -m scraper.main
```

You should see jobs appearing in your Notion database within a minute.

---

## Deploy to GitHub Actions

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "init: job scraper agent"
git remote add origin https://github.com/YOUR_USERNAME/job-scraper-agent.git
git push -u origin main
```

### 2. Add GitHub Secrets
Go to your repo → **Settings → Secrets → Actions → New repository secret**

Add these three secrets:
| Secret name | Value |
|---|---|
| `NOTION_TOKEN` | Your Notion integration token |
| `NOTION_DATABASE_ID` | From step 4 above |
| `GEMINI_API_KEY` | Your Gemini API key |

### 3. Enable Actions
Go to your repo → **Actions** tab → click **Enable GitHub Actions**

The scraper will now run daily at 8 AM IST automatically. You can also trigger it manually from the Actions tab.

---

## Customise

All customisation is in **`config.yaml`** — no code changes needed:

- **Add/remove job titles** → edit `search.queries`
- **Change locations** → edit `search.locations`
- **Adjust AI minimum score** → change `ai.min_score` (default: 40)
- **Add blocked keywords** → add to `filters.blocked_keywords`
- **Change schedule** → edit the cron in `.github/workflows/scraper.yml`

---

## Learning from your decisions

After reviewing jobs in Notion and setting their Status (Saved/Applied/Interested vs Skip/Rejected), run:

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
import os
from notion_client import Client
from ai.memory import sync_from_notion
import yaml
cfg = yaml.safe_load(open('config.yaml').read())
fb_cfg = cfg['feedback']
sync_from_notion(
    Client(auth=os.environ['NOTION_TOKEN']),
    os.environ['NOTION_DATABASE_ID'],
    fb_cfg['positive_statuses'],
    fb_cfg['negative_statuses']
)
"
```

This updates `data/feedback.json` which the AI uses to bias future scoring. Commit and push this file to persist it in GitHub Actions.

---

## Backfill AI scores on old rows

```bash
python enrich_existing.py
```

---

## Generate tailored cover letters

For your top-scored jobs, auto-draft a tailored, one-page cover letter using your CV
and the full job description. Each letter is saved to `applications/` and written into
the matching Notion page (the "Cover Letter" checkbox is ticked).

```bash
python generate_cover_letters.py              # top 5 jobs scoring >= 85
python generate_cover_letters.py --min 90     # only jobs scoring >= 90
python generate_cover_letters.py --count 10   # top 10
```

- Skips jobs you've marked Skip/Rejected and jobs that already have a letter
- Honest by design: it won't invent experience or overstate years — it leans on
  transferable strengths when there's a gap
- Tune defaults in `config.yaml` under `cover_letters:`

---

## Free tier limits

| Service | Free allowance | This agent uses |
|---|---|---|
| Gemini 2.5 Flash | 500 req/day | ~10-20 req/day |
| GitHub Actions | Unlimited (public repo) | ~5-10 min/day |
| Notion API | Unlimited | ~50-200 writes/day |

---

## Project structure

```
job-scraper-agent/
├── config.yaml              ← customise here
├── profile/context.md       ← your CV context for AI
├── scraper/
│   ├── main.py              ← orchestrator
│   ├── filters.py           ← keyword pre-filter
│   └── sources/
│       ├── indeed.py        ← Indeed RSS scraper
│       ├── linkedin.py      ← LinkedIn scraper
│       └── iimjobs.py       ← IIMJobs scraper
├── ai/
│   ├── client.py            ← Gemini client (auto-fallback)
│   ├── pipeline.py          ← batch scoring
│   └── memory.py            ← feedback learning
├── storage/notion_sync.py   ← Notion integration
├── data/feedback.json       ← learns from your decisions
├── setup.py                 ← one-time Notion DB creation
├── enrich_existing.py       ← backfill AI scores
└── .github/workflows/scraper.yml
```
