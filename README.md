# 🤖 AI Code Reviewer Bot

[![CI](https://github.com/pushkarreddy-25/ai-code-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/pushkarreddy-25/ai-code-reviewer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3--70B-orange)](https://console.groq.com)
[![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready GitHub Pull Request review bot that automatically posts **line-by-line AI review comments** on every PR — using 3 parallel analysis tracks.

> **Live Demo:** [ai-code-reviewer.onrender.com](https://ai-code-reviewer.onrender.com) &nbsp;|&nbsp; **Try it:** Open a PR in any connected repo and see comments appear within 30s.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧠 LLM Analysis | Deep semantic review via **Groq (Llama 3.3-70B)** — logic bugs, security flaws, performance issues |
| 🔍 AST Parser | Reliable static analysis for Python and JS/TS using Python's `ast` module |
| 📋 Rules Engine | Team-specific rules in a simple YAML file — zero code changes needed |
| 💬 Inline PR Comments | Comments on exact line numbers, just like a human reviewer |
| 📊 Live Dashboard | Real-time dashboard showing all reviews, findings, and stats |
| ⚡ Parallel Tracks | All 3 analysis tracks run simultaneously via `asyncio.gather` |
| 🔒 Webhook Security | HMAC-SHA256 signature verification on every webhook payload |
| 🚀 One-click Deploy | Ready for Render / Railway free tier via `render.yaml` |

---

## 🏗️ Architecture

```
GitHub PR Opened / Updated
         │
         ▼
  Webhook Server (FastAPI)
  [Verify HMAC Signature → Extract PR Context]
         │
  ┌──────┴──────┐
  │ asyncio.gather (parallel) │
  ├───────────────────────────┤
  │ Track A: Groq LLM         │  ← Semantic review via Llama 3.3-70B
  │ Track B: AST Parser       │  ← Python ast + JS regex heuristics
  │ Track C: Rules Engine     │  ← YAML-defined regex patterns
  └───────────────────────────┘
         │
  Deduplicate + Sort by Severity
         │
  Post Inline Review to GitHub PR
         │
  Update Live Dashboard
```

---

## 📁 Project Structure

```
ai-code-reviewer/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (lint + type check + tests)
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── routes/
│   │   ├── webhook.py           # GitHub webhook handler + HMAC verification
│   │   └── dashboard.py         # Dashboard REST API endpoints
│   └── services/
│       ├── pipeline.py          # Orchestrates all 3 analysis tracks
│       ├── groq_reviewer.py     # Groq LLM review track (Track A)
│       ├── ast_analyzer.py      # AST static analysis track (Track B)
│       ├── rules_engine.py      # Custom YAML rules track (Track C)
│       ├── github_client.py     # GitHub REST API client
│       └── review_store.py      # Thread-safe persistent review storage
├── dashboard/
│   └── index.html               # Live monitoring dashboard (Vanilla JS)
├── config/
│   └── rules.yaml               # Your custom team rules
├── tests/
│   ├── test_vulnerabilities.py  # Sample file that triggers all detectors
│   ├── test_webhook.py          # Webhook handler tests
│   └── test_local.py            # Local integration tests
├── .env.example                 # Environment variable template
├── render.yaml                  # Render deployment config
└── requirements.txt
```

---

## 🚀 Setup Guide

### Step 1 — Clone & Install

```bash
git clone https://github.com/pushkarreddy-25/ai-code-reviewer
cd ai-code-reviewer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2 — Get Your API Keys

**Groq API Key (free):**
1. Go to [console.groq.com](https://console.groq.com)
2. API Keys → Create Key
3. Copy the key (starts with `gsk_...`)

**GitHub Personal Access Token:**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. Select scopes: `repo` (full) + `pull_requests`
4. Copy the token (starts with `ghp_...`)

### Step 3 — Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### Step 4 — Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) to see the dashboard.

For local webhook testing, use ngrok:
```bash
ngrok http 8000
# Copy the https://xxxx.ngrok.io URL — use this as your webhook URL in GitHub
```

### Step 5 — Deploy to Render (Free)

1. Push code to GitHub:
```bash
git add .
git commit -m "deploy: initial setup"
git push origin main
```

2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Add your env vars in the Render dashboard:
   - `GROQ_API_KEY`
   - `GITHUB_TOKEN`
   - `GITHUB_WEBHOOK_SECRET`
5. Click Deploy → your URL: `https://ai-code-reviewer.onrender.com`

### Step 6 — Connect GitHub Webhook

1. Go to your target repo → Settings → Webhooks → Add webhook
2. Fill in:
   - **Payload URL:** `https://your-render-url.onrender.com/webhook/github`
   - **Content type:** `application/json`
   - **Secret:** same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
   - **Events:** Select "Pull requests" only
3. Click Add webhook ✅

---

## 🧪 Testing

Create a PR with `tests/test_vulnerabilities.py` to trigger all detectors:

```python
import os

# Triggers: hardcoded secret (CRITICAL)
password = "super_secret_admin_123"

# Triggers: SQL injection (CRITICAL)
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# Triggers: nested loop O(n²) (WARNING)
def find_pairs(items):
    results = []
    for item in items:
        for other in items:
            results.append((item, other))
    return results

# Triggers: bare except (WARNING)
def risky():
    try:
        do_something()
    except:
        pass

# Triggers: print in production (SUGGESTION)
print("debug output here")
```

The bot should post comments within **30 seconds**.

---

## ⚙️ Adding Custom Rules

Edit `config/rules.yaml`:

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

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Web server | FastAPI + Uvicorn |
| LLM | Groq API — Llama 3.3-70B Versatile |
| AST parsing | Python `ast` module + JS regex heuristics |
| HTTP client | `httpx` (fully async) |
| GitHub API | REST API v3 via httpx |
| Storage | Thread-safe JSON file (persistent, 200-item LRU) |
| Deployment | Render free tier |
| Dashboard | Vanilla JS + CSS (zero dependencies) |
| CI | GitHub Actions (Ruff lint + mypy + pytest) |

---

## 🎯 Interview Talking Points

When presenting this project, highlight:

1. **`asyncio.gather`** — 3 analysis tracks run in parallel, not sequentially
2. **Structured JSON prompting** — system prompt forces valid JSON output from the LLM
3. **HMAC-SHA256 webhook verification** — rejects spoofed payloads before any processing
4. **GitHub Pull Request Review API** — uses the official review endpoint (inline comments at specific lines), not plain issue comments
5. **Thread-safe storage** — `threading.Lock()` protects the in-memory store from concurrent webhook requests
6. **Deduplication logic** — findings from all 3 tracks are merged and deduplicated by `(file, line, category)` before posting

---

## 📄 License

MIT © [Pushkar Karri](https://github.com/pushkarreddy-25)
