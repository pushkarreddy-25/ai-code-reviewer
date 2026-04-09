"""
Test script — simulates a GitHub webhook with a deliberately buggy PR.
Run this while your server is running to test the full pipeline locally.

Usage:
    python test_webhook.py
"""

import hashlib
import hmac
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Simulated PR payload ──────────────────────────────────────────────────────

FAKE_PR_PAYLOAD = {
    "action": "opened",
    "pull_request": {
        "number": 42,
        "title": "Add user authentication endpoint",
        "body": "This PR adds login functionality with database queries.",
        "user": {"login": "test-developer"},
        "base": {"sha": "abc123def456"},
        "head": {"sha": "xyz789uvw012"},
    },
    "repository": {
        "full_name": "test-org/demo-repo",
    },
}

# ── Simulated file diff (deliberately contains bugs) ─────────────────────────

BUGGY_CODE = '''
import os

def login_user(username, password):
    # BUG 1: SQL injection vulnerability
    query = "SELECT * FROM users WHERE username = '%s' AND password = '%s'" % (username, password)
    
    # BUG 2: Hardcoded secret
    SECRET_KEY = "super_secret_password_123"
    
    try:
        result = db.execute(query)
    except:  # BUG 3: Bare except
        pass
    
    # BUG 4: print in production
    print(f"Login attempt for {username}")
    
    # BUG 5: Nested loops (O(n²))
    for user in result:
        for perm in user.permissions:
            check_permission(user, perm)
    
    return result
'''

# ── Monkey-patch github_client to return fake diff ───────────────────────────

async def mock_get_pr_diff(self, repo, pr_number):
    return [{
        "filename": "auth/login.py",
        "extension": "py",
        "status": "modified",
        "patch": "\n".join([f"+{line}" for line in BUGGY_CODE.split("\n")]),
        "full_content": BUGGY_CODE,
        "additions": 20,
        "deletions": 0,
        "changes": 20,
    }]


async def mock_post_review(self, repo, pr_number, findings, summary):
    print("\n" + "═" * 60)
    print("📬 REVIEW THAT WOULD BE POSTED TO GITHUB:")
    print("═" * 60)
    print(f"\n📝 Summary:\n{summary}\n")
    print(f"Found {len(findings)} issues:\n")
    for f in findings:
        sev = f.get("severity", "?").upper()
        icons = {"CRITICAL": "🚨", "WARNING": "⚠️", "SUGGESTION": "💡"}
        icon = icons.get(sev, "•")
        print(f"  {icon} [{sev}] {f.get('file')}:{f.get('line')} — {f.get('comment', '')[:80]}")
        print(f"     Source: {f.get('source', '?')}")
        print()


def send_test_webhook(server_url: str = "http://localhost:8000"):
    import asyncio
    from unittest.mock import patch

    # Patch GitHub client to avoid real API calls
    from app.services import github_client
    github_client.GitHubClient.get_pr_diff = mock_get_pr_diff
    github_client.GitHubClient.post_review = mock_post_review

    payload_bytes = json.dumps(FAKE_PR_PAYLOAD).encode()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    sig = "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest() if secret else ""

    print("🚀 Sending test webhook to", server_url)
    print("📦 PR: #42 — Add user authentication endpoint")
    print("🐛 Buggy code includes: SQL injection, hardcoded secret, bare except, print(), nested loops\n")

    response = httpx.post(
        f"{server_url}/webhook/github",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
        },
    )

    print(f"✅ Webhook accepted: {response.json()}")
    print("\n⏳ Review running in background... check dashboard at http://localhost:8000")
    print("   Or watch server logs for progress.")


if __name__ == "__main__":
    send_test_webhook()
