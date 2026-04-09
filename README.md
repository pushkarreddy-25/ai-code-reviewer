# 🤖 AI Code Reviewer Bot

A production-ready GitHub Pull Request review bot powered by **Claude AI**, AST static analysis,
and a custom rules engine. Automatically posts line-by-line review comments on every PR.

---

## Features

| Feature | Details |
|---|---|
| Claude AI Analysis | Deep semantic review — logic bugs, security flaws, performance issues |
| AST Parser | Reliable static analysis for Python and JS/TS |
| Custom Rules Engine | Team-specific rules in a simple YAML file |
| Inline PR Comments | Comments on exact line numbers, just like a human reviewer |
| Live Dashboard | Real-time dashboard showing all reviews and findings |
| Parallel Tracks | All 3 analysis tracks run simultaneously via asyncio |
| One-click Deploy | Ready for Render / Railway free tier |

---

## Architecture

```
GitHub PR Opened/Updated
        |
        v
  Webhook Server (FastAPI)
  [ Verify Signature -> Extract PR Context ]
        |
  3 Parallel Tracks (asyncio.gather)
  [ Track A: Claude AI ] + [ Track B: AST Parser ] + [ Track C: Rules YAML ]
        |
  Merge & Deduplicate Findings
        |
  Post Inline Review to GitHub
        |
  Update Live Dashboard
```

---

## Project Structure

```
ai-code-reviewer/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── routes/
│   │   ├── webhook.py           # GitHub webhook handler
│   │   └── dashboard.py        # Dashboard API endpoints
│   └── services/
│       ├── pipeline.py          # Orchestrates all 3 tracks
│       ├── claude_reviewer.py   # Claude AI analysis (Track A)
│       ├── ast_analyzer.py      # AST static analysis (Track B)
│       ├── rules_engine.py      # Custom rules engine (Track C)
│       ├── github_client.py     # GitHub API client
│       └── review_store.py      # Persistent review storage
├── dashboard/
│   └── index.html               # Live monitoring dashboard
├── config/
│   └── rules.yaml               # Your custom team rules
├── .env.example
├── requirements.txt
└── render.yaml                  # Render deployment config
```

---

## Setup Guide

### Step 1 — Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-code-reviewer
cd ai-code-reviewer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2 — Get Your API Keys

**Anthropic API Key:**
1. Go to https://console.anthropic.com
2. API Keys -> Create Key
3. Copy the key (starts with sk-ant-...)

**GitHub Personal Access Token:**
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: repo (full) + pull_requests
4. Copy the token (starts with ghp_...)

### Step 3 — Set Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in your 3 keys
```

### Step 4 — Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 to see the dashboard.

For local webhook testing, use ngrok:
```bash
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL — use this as your webhook URL
```

### Step 5 — Deploy to Render (Free)

1. Push code to GitHub:
```bash
git add .
git commit -m "Initial deploy"
git push origin main
```

2. Go to https://render.com -> New -> Web Service
3. Connect your GitHub repo
4. Render auto-detects render.yaml
5. Add your 3 environment variables in the Render dashboard:
   - ANTHROPIC_API_KEY
   - GITHUB_TOKEN
   - GITHUB_WEBHOOK_SECRET
6. Click Deploy
7. Your URL will be: https://ai-code-reviewer.onrender.com

### Step 6 — Connect GitHub Webhook

1. Go to your target repo -> Settings -> Webhooks -> Add webhook
2. Fill in:
   - Payload URL: https://your-render-url.onrender.com/webhook/github
   - Content type: application/json
   - Secret: same value as GITHUB_WEBHOOK_SECRET in your .env
   - Events: Select "Pull requests" only
3. Click Add webhook

---

## Testing

Create a PR with this file to test all detections:

```python
# test_vulnerabilities.py
import os

# Should trigger: hardcoded secret (CRITICAL)
password = "super_secret_admin_123"

# Should trigger: SQL injection (CRITICAL)
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# Should trigger: nested loop O(n2) (WARNING)
def find_pairs(items):
    results = []
    for item in items:
        for other in items:
            results.append((item, other))
    return results

# Should trigger: bare except (WARNING)
def risky():
    try:
        do_something()
    except:
        pass

# Should trigger: print in production (SUGGESTION)
print("debug output here")
```

The bot should post comments within 30 seconds.

---

## Adding Custom Rules

Edit config/rules.yaml:

```yaml
rules:
  - id: no-direct-db-in-routes
    pattern: "db\\.execute|cursor\\.execute"
    files: "*/routes/*.py"
    severity: warning
    category: maintainability
    message: "Direct DB calls in routes violate separation of concerns. Use a service layer."
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web server | FastAPI + Uvicorn |
| LLM | Anthropic Claude claude-opus-4-5 |
| AST parsing | Python ast module |
| HTTP client | httpx (async) |
| GitHub API | REST API via httpx |
| Storage | JSON file (persistent) |
| Deployment | Render free tier |
| Dashboard | Vanilla JS + CSS |

---

## Demo Script (For Placement Interviews)

1. Open a PR with test_vulnerabilities.py
2. Show webhook firing in Render logs (real-time)
3. Show bot posting inline comments on GitHub within 30s
4. Show dashboard updating automatically
5. Open a clean PR to show zero false positives
6. Explain the 3-track parallel architecture

Key points to mention:
- asyncio.gather for parallel execution
- Structured JSON prompting for reliable LLM output
- HMAC webhook signature verification
- GitHub Pull Request Review API (not plain comments)
- Persistent storage with JSON fallback
