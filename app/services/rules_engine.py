import re
from pathlib import Path

import yaml


DEFAULT_RULES = [
    {
        "id": "no-hardcoded-secrets",
        "pattern": r"(password|secret|api_key|token|passwd)\s*=\s*['\"][^'\"]{4,}['\"]",
        "severity": "critical",
        "category": "security",
        "message": "Possible hardcoded secret detected. Move this to environment variables or a secrets manager immediately.",
        "files": "*",
        "flags": re.IGNORECASE,
    },
    {
        "id": "no-sql-string-format",
        "pattern": r"(execute|cursor\.execute|query)\s*\(\s*['\"].*(%s|format\(|f['\"])",
        "severity": "critical",
        "category": "security",
        "message": "Possible SQL injection: string formatting detected inside a query. Use parameterized queries with `?` or `%s` placeholders and pass values separately.",
        "files": "*.py",
    },
    {
        "id": "no-print-production",
        "pattern": r"^\s*print\s*\(",
        "severity": "suggestion",
        "category": "style",
        "message": "Use `logging.info()` / `logging.debug()` instead of `print()` for production code.",
        "files": "*.py",
    },
    {
        "id": "no-todo-critical",
        "pattern": r"#\s*TODO.*urgent|#\s*FIXME.*critical|#\s*HACK",
        "severity": "warning",
        "category": "maintainability",
        "message": "Critical TODO/FIXME/HACK comment found. Resolve before merging or create a tracked issue.",
        "files": "*",
        "flags": re.IGNORECASE,
    },
    {
        "id": "no-debugger",
        "pattern": r"\bdebugger\b",
        "severity": "warning",
        "category": "style",
        "message": "`debugger` statement left in code — remove before merging to production.",
        "files": "*.js,*.ts,*.jsx,*.tsx",
    },
    {
        "id": "no-innerHTML",
        "pattern": r"\.innerHTML\s*=",
        "severity": "warning",
        "category": "security",
        "message": "Setting `innerHTML` directly can lead to XSS attacks. Use `textContent` for plain text, or DOMPurify to sanitize HTML.",
        "files": "*.js,*.ts,*.jsx,*.tsx",
    },
    {
        "id": "no-exec-shell",
        "pattern": r"os\.system\(|subprocess\.call\(|subprocess\.Popen\(",
        "severity": "warning",
        "category": "security",
        "message": "Shell execution detected. Avoid `shell=True` and validate/sanitize all inputs to prevent command injection.",
        "files": "*.py",
    },
]


class RulesEngine:
    def __init__(self, rules_path: str = "config/rules.yaml"):
        self.rules = self._load_rules(rules_path)

    def _load_rules(self, path: str) -> list:
        rules = list(DEFAULT_RULES)
        try:
            if Path(path).exists():
                with open(path) as f:
                    custom = yaml.safe_load(f)
                    if custom and "rules" in custom:
                        rules.extend(custom["rules"])
        except Exception as e:
            print(f"Rules load warning: {e}")
        return rules

    def _matches_file(self, filename: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        extensions = [p.strip().lstrip("*.") for p in pattern.split(",")]
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        return ext in extensions

    def check(self, file_info: dict) -> list:
        filename = file_info.get("filename", "")
        content = file_info.get("full_content", "") or file_info.get("patch", "")

        if not content:
            return []

        findings = []
        lines = content.split("\n")

        for rule in self.rules:
            file_pattern = rule.get("files", "*")
            if not self._matches_file(filename, file_pattern):
                continue

            pattern = rule.get("pattern", "")
            flags = rule.get("flags", 0)

            try:
                compiled = re.compile(pattern, flags)
            except re.error:
                continue

            for i, line in enumerate(lines, start=1):
                # Only check added lines in diffs
                if content.startswith("@@") and not line.startswith("+"):
                    continue

                if compiled.search(line):
                    findings.append({
                        "file": filename,
                        "line": i,
                        "severity": rule.get("severity", "warning"),
                        "category": rule.get("category", "style"),
                        "comment": rule.get("message", "Rule violation detected."),
                        "source": f"Rules Engine ({rule.get('id', 'custom')})",
                    })
                    break  # one finding per rule per file

        return findings
