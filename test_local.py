"""
Local test script — simulates a full PR review WITHOUT needing GitHub.
Run this to verify your API keys and pipeline work correctly.

Usage:
    python test_local.py
"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ast_analyzer import ASTAnalyzer
from app.services.claude_reviewer import ClaudeReviewer
from app.services.rules_engine import RulesEngine

# ── Sample vulnerable file to test against ──────────────────────────────────
SAMPLE_FILE = {
    "filename": "app/routes/users.py",
    "extension": "py",
    "status": "modified",
    "patch": """\
@@ -1,5 +1,35 @@
+import os
+
+# Hardcoded credentials
+DB_PASSWORD = "admin1234secret"
+API_KEY = "sk-prod-abc123xyz789"
+
+def get_user_by_id(user_id):
+    # SQL injection vulnerability
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    result = db.execute(query)
+    return result
+
+def find_duplicate_users(users):
+    duplicates = []
+    for user in users:
+        for other_user in users:
+            if user['email'] == other_user['email'] and user != other_user:
+                duplicates.append(user)
+    return duplicates
+
+def process_request(data):
+    try:
+        return handle(data)
+    except:
+        pass
+
+def send_notification(user, msg, retry, log, db, cache, queue, metrics):
+    print(f"Sending to {user}")
+    pass
""",
    "full_content": """\
import os

DB_PASSWORD = "admin1234secret"
API_KEY = "sk-prod-abc123xyz789"

def get_user_by_id(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = db.execute(query)
    return result

def find_duplicate_users(users):
    duplicates = []
    for user in users:
        for other_user in users:
            if user['email'] == other_user['email'] and user != other_user:
                duplicates.append(user)
    return duplicates

def process_request(data):
    try:
        return handle(data)
    except:
        pass

def send_notification(user, msg, retry, log, db, cache, queue, metrics):
    print(f"Sending to {user}")
    pass
""",
    "additions": 28,
    "deletions": 0,
    "changes": 28,
}

SAMPLE_PR = {
    "repo": "test-user/test-repo",
    "pr_number": 42,
    "pr_title": "Add user routes and notification system",
    "pr_body": "Adds user lookup and notification sending functionality.",
    "author": "test-developer",
    "head_sha": "abc1234",
}


async def run_test():
    print("\n" + "="*60)
    print("  AI CODE REVIEWER — LOCAL TEST")
    print("="*60 + "\n")

    # ── Track B: AST ────────────────────────────────────────────
    print("▶ Track B: AST Analyzer...")
    ast = ASTAnalyzer()
    ast_findings = ast.analyze(SAMPLE_FILE)
    print(f"  Found {len(ast_findings)} issues\n")
    for f in ast_findings:
        print(f"  [{f['severity'].upper()}] Line {f['line']}: {f['comment'][:80]}...")

    print()

    # ── Track C: Rules Engine ───────────────────────────────────
    print("▶ Track C: Rules Engine...")
    rules = RulesEngine("config/rules.yaml")
    rule_findings = rules.check(SAMPLE_FILE)
    print(f"  Found {len(rule_findings)} issues\n")
    for f in rule_findings:
        print(f"  [{f['severity'].upper()}] Line {f['line']}: {f['comment'][:80]}...")

    print()

    # ── Track A: Claude AI ──────────────────────────────────────
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant-xxx"):
        print("▶ Track A: Claude AI... SKIPPED (no API key in .env)\n")
        llm_findings = []
    else:
        print("▶ Track A: Claude AI (this takes 5-10 seconds)...")
        claude = ClaudeReviewer(api_key)
        llm_findings = await claude.review_diff(SAMPLE_PR, [SAMPLE_FILE])
        print(f"  Found {len(llm_findings)} issues\n")
        for f in llm_findings:
            print(f"  [{f['severity'].upper()}] Line {f.get('line','?')}: {f['comment'][:80]}...")
        print()

        # Test summary
        all_findings = ast_findings + rule_findings + llm_findings
        print("▶ Generating PR Summary...")
        summary = await claude.generate_summary(SAMPLE_PR, all_findings)
        print(f"\n  Summary: {summary}\n")

    # ── Final Report ────────────────────────────────────────────
    all_findings = ast_findings + rule_findings + llm_findings
    print("="*60)
    print(f"  TOTAL FINDINGS: {len(all_findings)}")
    print(f"  Critical: {sum(1 for f in all_findings if f.get('severity')=='critical')}")
    print(f"  Warning:  {sum(1 for f in all_findings if f.get('severity')=='warning')}")
    print(f"  Suggestion: {sum(1 for f in all_findings if f.get('severity')=='suggestion')}")
    print("="*60)
    print("\n✅ Test complete! If you see findings above, your pipeline works.\n")


if __name__ == "__main__":
    asyncio.run(run_test())
