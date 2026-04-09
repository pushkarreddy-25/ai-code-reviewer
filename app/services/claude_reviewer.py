import json
import os
import re

from groq import Groq


SYSTEM_PROMPT = """You are a senior software engineer performing a thorough code review on a pull request.

Your job is to find REAL bugs, security vulnerabilities, performance issues, and maintainability problems.

You MUST respond with a valid JSON array only. No explanation text before or after. No markdown fences.

Each finding must follow this exact schema:
[
  {
    "file": "relative/path/to/file.py",
    "line": 42,
    "severity": "critical",
    "category": "security",
    "comment": "Clear explanation of the problem AND a concrete suggested fix"
  }
]

Severity must be one of: critical, warning, suggestion
Category must be one of: security, performance, logic, maintainability, style

Severity guide:
- critical: SQL injection, hardcoded secrets, XSS, crashes, data corruption
- warning: Logic bugs, unhandled exceptions, O(n2) loops, missing null checks
- suggestion: Dead code, better naming, missing tests, refactoring

IMPORTANT rules:
- Only report issues in ADDED lines (lines starting with + in the diff)
- Line numbers must be real line numbers in the final file
- If no real issues exist, return an empty array: []
- Maximum 10 findings per review
- Be specific: mention variable names, function names, exact problem"""


class ClaudeReviewer:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", api_key))

    async def review_diff(self, pr_data: dict, diff_files: list) -> list:
        if not diff_files:
            return []

        files_context = ""
        for f in diff_files:
            files_context += f"\n\n### FILE: {f['filename']} ({f['status']})\n"
            files_context += f"**Diff:**\n```\n{f['patch'][:3000]}\n```\n"
            if f["full_content"]:
                files_context += f"**Full content:**\n```{f['extension']}\n{f['full_content'][:2000]}\n```\n"

        user_message = f"""PR Title: {pr_data['pr_title']}
PR Description: {pr_data.get('pr_body', 'No description')}
Author: {pr_data['author']}
Repository: {pr_data['repo']}

{files_context}

Review the above changes. Return ONLY a JSON array of findings."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"^```\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            findings = json.loads(raw)

            validated = []
            for f in findings:
                if isinstance(f, dict) and "file" in f and "comment" in f:
                    f["source"] = "Groq AI (Llama 3.3)"
                    f["line"] = int(f.get("line", 1))
                    validated.append(f)

            return validated

        except json.JSONDecodeError as e:
            print(f"Groq returned invalid JSON: {e}\nRaw: {raw[:300]}")
            return []
        except Exception as e:
            print(f"Groq API error: {e}")
            return []

    async def generate_summary(self, pr_data: dict, findings: list) -> str:
        if not findings:
            return "No significant issues found. This PR looks good to merge!"

        findings_text = "\n".join([
            f"- [{f['severity'].upper()}] {f.get('file','?')}:{f.get('line','?')} — {f.get('comment','')[:100]}"
            for f in findings[:6]
        ])

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""Write a 2-3 sentence PR review summary.
PR: {pr_data['pr_title']}
Findings:
{findings_text}

Be direct. Start with overall assessment. Mention the most important issue."""
                }],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary error: {e}")
            critical = sum(1 for f in findings if f.get("severity") == "critical")
            warning = sum(1 for f in findings if f.get("severity") == "warning")
            return f"Found {critical} critical issues and {warning} warnings that should be addressed before merging."