import asyncio
import os
import traceback
from datetime import datetime

from app.services.ast_analyzer import ASTAnalyzer
from app.services.groq_reviewer import GroqReviewer
from app.services.github_client import GitHubClient
from app.services.rules_engine import RulesEngine


class ReviewPipeline:
    def __init__(self, store):
        self.store = store
        self.github = GitHubClient(os.getenv("GITHUB_TOKEN", ""))
        self.claude = GroqReviewer()
        self.ast = ASTAnalyzer()
        self.rules = RulesEngine()

    async def run(self, pr_data: dict):
        review_id = f"{pr_data['repo'].replace('/', '_')}_{pr_data['pr_number']}_{pr_data['head_sha'][:7]}"

        self.store.upsert(review_id, {
            "id": review_id,
            "repo": pr_data["repo"],
            "pr_number": pr_data["pr_number"],
            "pr_title": pr_data["pr_title"],
            "author": pr_data["author"],
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "findings": [],
            "summary": "",
        })

        try:
            # Step 1: Fetch diff from GitHub
            diff_files = await self.github.get_pr_diff(
                pr_data["repo"], pr_data["pr_number"]
            )

            if not diff_files:
                self.store.upsert(review_id, {"status": "skipped", "summary": "No reviewable files found."})
                return

            all_findings = []

            # Step 2: Run 3 tracks in parallel
            track_results = await asyncio.gather(
                self._run_llm_track(pr_data, diff_files),
                self._run_ast_track(diff_files),
                self._run_rules_track(diff_files),
                return_exceptions=True,
            )

            for result in track_results:
                if isinstance(result, list):
                    all_findings.extend(result)
                elif isinstance(result, Exception):
                    print(f"Track error: {result}")

            # Deduplicate by (file, line, category)
            seen = set()
            unique_findings = []
            for f in all_findings:
                key = (f.get("file"), f.get("line"), f.get("category"))
                if key not in seen:
                    seen.add(key)
                    unique_findings.append(f)

            # Sort: critical first
            severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
            unique_findings.sort(key=lambda x: severity_order.get(x.get("severity", "suggestion"), 2))

            # Step 3: Generate summary
            summary = await self.claude.generate_summary(pr_data, unique_findings)

            # Step 4: Post review to GitHub
            await self.github.post_review(
                pr_data["repo"],
                pr_data["pr_number"],
                unique_findings,
                summary,
            )

            # Step 5: Update store
            self.store.upsert(review_id, {
                "status": "completed",
                "findings": unique_findings,
                "summary": summary,
                "completed_at": datetime.utcnow().isoformat(),
                "stats": {
                    "total": len(unique_findings),
                    "critical": sum(1 for f in unique_findings if f.get("severity") == "critical"),
                    "warning": sum(1 for f in unique_findings if f.get("severity") == "warning"),
                    "suggestion": sum(1 for f in unique_findings if f.get("severity") == "suggestion"),
                }
            })

        except Exception as e:
            traceback.print_exc()
            self.store.upsert(review_id, {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat(),
            })

    async def _run_llm_track(self, pr_data: dict, diff_files: list) -> list:
        return await self.claude.review_diff(pr_data, diff_files)

    async def _run_ast_track(self, diff_files: list) -> list:
        findings = []
        for file in diff_files:
            findings.extend(self.ast.analyze(file))
        return findings

    async def _run_rules_track(self, diff_files: list) -> list:
        findings = []
        for file in diff_files:
            findings.extend(self.rules.check(file))
        return findings
