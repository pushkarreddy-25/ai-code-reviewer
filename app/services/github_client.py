import re
from typing import Optional

import httpx


class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_diff(self, repo: str, pr_number: int) -> list[dict]:
        """Fetch PR files with their diffs and full content."""
        async with httpx.AsyncClient(timeout=30) as client:
            # Get list of changed files
            resp = await client.get(
                f"{self.BASE}/repos/{repo}/pulls/{pr_number}/files",
                headers=self.headers,
                params={"per_page": 30},
            )
            resp.raise_for_status()
            files = resp.json()

        result = []
        async with httpx.AsyncClient(timeout=30) as client:
            for f in files:
                filename = f["filename"]
                status = f["status"]  # added, modified, removed

                if status == "removed":
                    continue

                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                supported = ["py", "js", "ts", "jsx", "tsx", "java", "go", "cs", "cpp", "c", "rb", "php"]

                if ext not in supported:
                    continue

                # Try to get full file content
                full_content = ""
                try:
                    content_resp = await client.get(
                        f["raw_url"], headers={"Authorization": f"Bearer {self.token}"}
                    )
                    if content_resp.status_code == 200:
                        full_content = content_resp.text[:8000]  # cap at 8k chars
                except Exception:
                    pass

                result.append({
                    "filename": filename,
                    "extension": ext,
                    "status": status,
                    "patch": f.get("patch", ""),
                    "full_content": full_content,
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "changes": f["changes"],
                })

        return result

    async def post_review(self, repo: str, pr_number: int, findings: list, summary: str):
        """Post inline review comments to the PR."""
        # Only post inline comments for critical/warning (not suggestions — too noisy)
        comments = []
        for f in findings:
            if f.get("severity") in ["critical", "warning"] and f.get("line"):
                emoji = "🚨" if f["severity"] == "critical" else "⚠️"
                category = f.get("category", "").upper()
                body = (
                    f"{emoji} **[{f['severity'].upper()}]** `{category}`\n\n"
                    f"{f['comment']}\n\n"
                    f"*Detected by: {f.get('source', 'AI Review')}*"
                )
                comments.append({
                    "path": f["file"],
                    "line": f["line"],
                    "body": body,
                    "side": "RIGHT",
                })

        # Build review body
        critical_count = sum(1 for f in findings if f.get("severity") == "critical")
        warning_count = sum(1 for f in findings if f.get("severity") == "warning")
        suggestion_count = sum(1 for f in findings if f.get("severity") == "suggestion")

        review_event = "REQUEST_CHANGES" if critical_count > 0 else "COMMENT"

        body = f"""## 🤖 AI Code Review

{summary}

---
**Summary:** 🚨 {critical_count} Critical &nbsp;|&nbsp; ⚠️ {warning_count} Warnings &nbsp;|&nbsp; 💡 {suggestion_count} Suggestions

<details>
<summary>💡 All Suggestions</summary>

"""
        for f in findings:
            if f.get("severity") == "suggestion":
                body += f"- **{f.get('file', 'unknown')}:{f.get('line', '?')}** — {f.get('comment', '')}\n"

        body += "\n</details>\n\n*Powered by Claude AI + AST Analysis*"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE}/repos/{repo}/pulls/{pr_number}/reviews",
                headers=self.headers,
                json={
                    "body": body,
                    "event": review_event,
                    "comments": comments[:10],  # GitHub caps at some limit
                },
            )
            if resp.status_code not in [200, 201]:
                print(f"GitHub review post failed: {resp.status_code} {resp.text}")
