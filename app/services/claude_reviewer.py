import json
import re

import anthropic


SYSTEM_PROMPT = """You are a senior software engineer performing a thorough code review on a pull request.

Your job is to find REAL bugs, security vulnerabilities, performance issues, and maintainability problems — not nitpick style or add fluff.

You MUST respond with a valid JSON array only. No explanation text before or after. No markdown fences.

Each finding must follow this exact schema:
[
  {
    "file": "relative/path/to/file.py",
    "line": 42,
    "severity": "critical" | "warning" | "suggestion",
    "category": "security" | "performance" | "logic" | "maintainability" | "style",
    "comment": "Clear explanation of the problem AND a concrete suggested fix"
  }
]

Severity guide:
- critical: Security vulnerabilities (SQL injection, XSS, hardcoded secrets, unvalidated input), crashes, data corruption
- warning: Logic bugs, unhandled exceptions, O(n²) in hot paths, memory leaks, missing null checks
- suggestion: Code clarity, dead code, missing tests, better naming, refactoring opportunities

IMPORTANT rules:
- Only report issues in ADDED lines (lines starting with + in the diff)
- Line numbers must be real line numbers in the final file, not diff offsets
- If no real issues exist, return an empty array: []
- Maximum 15 findings per review
- Be specific: mention variable names, function names, exact problem"""


class ClaudeReviewer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def review_diff(self, pr_data: dict, diff_files: list) -> list:
        """Run LLM analysis on the PR diff."""
        if not diff_files:
            return []

        # Build context message
        files_context = ""
        for f in diff_files:
            files_context += f"\n\n### FILE: {f['filename']} ({f['status']})\n"
            files_context += f"**Diff (+ added, - removed):**\n```\n{f['patch'][:3000]}\n```\n"
            if f["full_content"]:
                files_context += f"**Full file content:**\n```{f['extension']}\n{f['full_content'][:3000]}\n```\n"

        user_message = f"""PR Title: {pr_data['pr_title']}
PR Description: {pr_data.get('pr_body', 'No description provided')}
Author: {pr_data['author']}
Repository: {pr_data['repo']}

{files_context}

Review the above changes and return your findings as a JSON array."""

        try:
            message = self.client.messages.create(
                model="claude-opus-4-5",
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            raw = message.content[0].text.strip()

            # Strip markdown fences if Claude added them
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            findings = json.loads(raw)

            # Validate and tag source
            validated = []
            for f in findings:
                if isinstance(f, dict) and "file" in f and "comment" in f:
                    f["source"] = "Claude AI"
                    f["line"] = int(f.get("line", 1))
                    validated.append(f)

            return validated

        except json.JSONDecodeError as e:
            print(f"Claude returned invalid JSON: {e}\nRaw: {raw[:500]}")
            return []
        except Exception as e:
            print(f"Claude API error: {e}")
            return []

    async def generate_summary(self, pr_data: dict, findings: list) -> str:
        """Generate a human-readable PR summary."""
        critical = [f for f in findings if f.get("severity") == "critical"]
        warnings = [f for f in findings if f.get("severity") == "warning"]

        if not findings:
            return "✅ No significant issues found. This PR looks good to merge!"

        findings_text = "\n".join([
            f"- [{f['severity'].upper()}] {f['file']}:{f.get('line', '?')} — {f['comment'][:100]}"
            for f in findings[:8]
        ])

        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Write a 2-3 sentence PR review summary for:
PR: {pr_data['pr_title']}
Findings:
{findings_text}

Be direct and helpful. Start with overall assessment. Mention the most important issue."""
            }],
        )

        return message.content[0].text.strip()
