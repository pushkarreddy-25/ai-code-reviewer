"""
Local integration test — runs the review pipeline against a sample diff.
Run with: python tests/test_local.py (requires GROQ_API_KEY in .env)
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.groq_reviewer import GroqReviewer
from app.services.ast_analyzer import ASTAnalyzer
from app.services.rules_engine import RulesEngine


SAMPLE_FILE = {
    "filename": "tests/test_vulnerabilities.py",
    "extension": "py",
    "status": "modified",
    "patch": """+password = "super_secret_admin_123"
+def get_user(user_id):
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)""",
    "full_content": open(
        os.path.join(os.path.dirname(__file__), "test_vulnerabilities.py"), "r"
    ).read() if os.path.exists(
        os.path.join(os.path.dirname(__file__), "test_vulnerabilities.py")
    ) else "",
    "additions": 5,
    "deletions": 0,
    "changes": 5,
}

PR_DATA = {
    "repo": "pushkarreddy-25/ai-code-reviewer",
    "pr_number": 999,
    "pr_title": "Test PR: adding vulnerable code",
    "pr_body": "Testing the review bot",
    "author": "pushkarreddy-25",
    "action": "opened",
    "base_sha": "abc123",
    "head_sha": "def456",
}


async def main():
    print("🔍 Running local review test...\n")

    # Track B: AST
    print("─ Track B: AST Analyzer")
    ast = ASTAnalyzer()
    ast_findings = ast.analyze(SAMPLE_FILE)
    for f in ast_findings:
        print(f"  [{f['severity'].upper()}] {f['file']}:{f['line']} — {f['comment'][:80]}")

    # Track C: Rules
    print("\n─ Track C: Rules Engine")
    rules = RulesEngine()
    rule_findings = rules.check(SAMPLE_FILE)
    for f in rule_findings:
        print(f"  [{f['severity'].upper()}] {f['file']}:{f['line']} — {f['comment'][:80]}")

    # Track A: Groq LLM
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        print("\n─ Track A: Groq LLM — ⚠️  GROQ_API_KEY not set, skipping")
    else:
        print("\n─ Track A: Groq LLM")
        reviewer = GroqReviewer(groq_key)
        llm_findings = await reviewer.review_diff(PR_DATA, [SAMPLE_FILE])
        for f in llm_findings:
            print(f"  [{f['severity'].upper()}] {f['file']}:{f['line']} — {f['comment'][:80]}")

    print(f"\n✅ Done — {len(ast_findings) + len(rule_findings)} static findings")


if __name__ == "__main__":
    asyncio.run(main())
