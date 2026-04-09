import ast
import re


class ASTAnalyzer:
    """Static analysis using AST parsing. Currently supports Python; JS via regex heuristics."""

    def analyze(self, file_info: dict) -> list:
        ext = file_info.get("extension", "")
        content = file_info.get("full_content", "")
        filename = file_info.get("filename", "")

        if not content:
            return []

        if ext == "py":
            return self._analyze_python(filename, content)
        elif ext in ["js", "ts", "jsx", "tsx"]:
            return self._analyze_js_heuristic(filename, content)
        return []

    def _analyze_python(self, filename: str, content: str) -> list:
        findings = []
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return [{
                "file": filename,
                "line": e.lineno or 1,
                "severity": "critical",
                "category": "logic",
                "comment": f"Syntax error: {e.msg}. This file will crash at import time.",
                "source": "AST Parser",
            }]

        for node in ast.walk(tree):
            # Check: bare except clause
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append({
                    "file": filename,
                    "line": node.lineno,
                    "severity": "warning",
                    "category": "maintainability",
                    "comment": "Bare `except:` catches ALL exceptions including KeyboardInterrupt and SystemExit. Use `except Exception:` at minimum, or catch specific exceptions.",
                    "source": "AST Parser",
                })

            # Check: functions with too many arguments (> 7)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_count = len(node.args.args) + len(node.args.posonlyargs)
                if arg_count > 7:
                    findings.append({
                        "file": filename,
                        "line": node.lineno,
                        "severity": "suggestion",
                        "category": "maintainability",
                        "comment": f"Function `{node.name}` has {arg_count} parameters. Consider using a dataclass or config object to reduce parameter count.",
                        "source": "AST Parser",
                    })

                # Check: very long functions (> 60 lines)
                func_lines = (node.end_lineno or node.lineno) - node.lineno
                if func_lines > 60:
                    findings.append({
                        "file": filename,
                        "line": node.lineno,
                        "severity": "suggestion",
                        "category": "maintainability",
                        "comment": f"Function `{node.name}` is {func_lines} lines long. Consider breaking it into smaller, focused functions.",
                        "source": "AST Parser",
                    })

            # Check: assert statements in non-test files
            if isinstance(node, ast.Assert) and "test" not in filename.lower():
                findings.append({
                    "file": filename,
                    "line": node.lineno,
                    "severity": "warning",
                    "category": "logic",
                    "comment": "Using `assert` for runtime checks is unsafe — assertions are disabled when Python runs with -O flag. Use explicit `if` checks with proper exceptions.",
                    "source": "AST Parser",
                })

            # Check: nested loops (potential O(n²))
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if child is not node and isinstance(child, (ast.For, ast.While)):
                        findings.append({
                            "file": filename,
                            "line": node.lineno,
                            "severity": "warning",
                            "category": "performance",
                            "comment": "Nested loop detected — potential O(n²) or worse complexity. Verify this is acceptable for your data sizes, or consider a hash-map based approach.",
                            "source": "AST Parser",
                        })
                        break  # only report once per outer loop

        return findings[:5]  # cap AST findings

    def _analyze_js_heuristic(self, filename: str, content: str) -> list:
        findings = []
        lines = content.split("\n")

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()

            # console.log in non-test files
            if "console.log(" in stripped and "test" not in filename.lower():
                findings.append({
                    "file": filename,
                    "line": i,
                    "severity": "suggestion",
                    "category": "style",
                    "comment": "Remove `console.log()` before merging to production. Use a proper logger instead.",
                    "source": "AST Parser",
                })

            # == instead of ===
            if re.search(r"[^!=<>]==[^=]", stripped) and "==" in stripped:
                findings.append({
                    "file": filename,
                    "line": i,
                    "severity": "warning",
                    "category": "logic",
                    "comment": "Use `===` (strict equality) instead of `==` to avoid implicit type coercion bugs in JavaScript.",
                    "source": "AST Parser",
                })

            # eval() usage
            if re.search(r"\beval\s*\(", stripped):
                findings.append({
                    "file": filename,
                    "line": i,
                    "severity": "critical",
                    "category": "security",
                    "comment": "`eval()` is a security risk — it can execute arbitrary code. Replace with JSON.parse() for data or refactor the logic.",
                    "source": "AST Parser",
                })

        return findings[:5]
