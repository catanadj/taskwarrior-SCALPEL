from __future__ import annotations

import argparse
import re
import shutil
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from ..process import run_command
from .result import ToolIssue, ToolResult, result_from_issues


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "scalpel" / "__init__.py").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _git_ignored_paths(root: Path, rel_paths: List[str]) -> Set[str]:
    """Return repo-relative paths ignored by git.

    This lets doctor suppress warnings for transient local outputs that are
    already covered by .gitignore while still flagging tracked/unignored
    artifacts.
    """

    if not rel_paths or shutil.which("git") is None or not (root / ".git").exists():
        return set()

    payload = "\0".join(rel_paths) + "\0"
    result = run_command(
        ["git", "check-ignore", "--stdin", "-z"],
        cwd=root,
        input_text=payload,
    )
    if result.returncode not in {0, 1}:
        return set()
    return {item for item in result.stdout.split("\0") if item}


def _issues_to_legacy_lists(issues: list[ToolIssue]) -> tuple[list[str], list[str]]:
    warnings = [issue.message for issue in issues if issue.level == "warning"]
    errors = [issue.message for issue in issues if issue.level == "error"]
    return warnings, errors


def _scan_tree(root: Path, *, verbose_artifacts: bool = False) -> Tuple[List[str], List[str]]:
    warnings, errors = _issues_to_legacy_lists(_scan_tree_issues(root, verbose_artifacts=verbose_artifacts))
    return warnings, errors


def _scan_tree_issues(root: Path, *, verbose_artifacts: bool = False) -> list[ToolIssue]:
    """Scan the repository for common hygiene issues.

    Keep this relatively conservative: focus on artifacts that tend to break
    releases (patch rejects, copy artifacts, bytecode) while avoiding deep
    semantic checks.
    """

    issues: list[ToolIssue] = []

    bad_name = re.compile(r"^Copy \(\d+\) ")
    skip_dirs = {".git", "build", "dist", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".ship-safe"}
    pycache_dirs: List[str] = []
    pyc_files: List[str] = []
    bak_files: List[str] = []
    copy_files: List[str] = []
    rej_files: List[str] = []
    orig_files: List[str] = []

    for p in root.rglob("*"):
        # Skip common generated directories.
        if any(part in skip_dirs for part in p.parts):
            continue

        rel = str(p.relative_to(root))

        if p.is_dir():
            if p.name == "__pycache__":
                pycache_dirs.append(rel)
            continue

        name = p.name

        if bad_name.search(name):
            copy_files.append(rel)
        if name.endswith(".rej"):
            rej_files.append(rel)
        if name.endswith(".orig"):
            orig_files.append(rel)

        if name.endswith(".pyc"):
            pyc_files.append(rel)
        if name.endswith(".bak"):
            bak_files.append(rel)

    ignored = _git_ignored_paths(
        root,
        pycache_dirs + pyc_files + bak_files + copy_files + rej_files + orig_files,
    )

    visible_pycache_dirs = [rel for rel in pycache_dirs if rel not in ignored]
    visible_pyc_files = [rel for rel in pyc_files if rel not in ignored]
    visible_bak_files = [rel for rel in bak_files if rel not in ignored]
    visible_copy_files = [rel for rel in copy_files if rel not in ignored]
    visible_rej_files = [rel for rel in rej_files if rel not in ignored]
    visible_orig_files = [rel for rel in orig_files if rel not in ignored]

    for rel in visible_copy_files:
        issues.append(ToolIssue("error", f"Stray copy artifact: {rel}"))
    for rel in visible_rej_files:
        issues.append(ToolIssue("error", f"Patch reject present: {rel}"))
    for rel in visible_orig_files:
        issues.append(ToolIssue("error", f"Patch artifact present: {rel}"))

    if verbose_artifacts:
        for rel in visible_pycache_dirs:
            issues.append(ToolIssue("warning", f"Found __pycache__ directory: {rel} (consider cleaning it)"))
        for rel in visible_pyc_files:
            issues.append(ToolIssue("warning", f"Bytecode file present: {rel} (consider cleaning)"))
        for rel in visible_bak_files:
            issues.append(ToolIssue("warning", f"Backup file present: {rel} (ok, but consider cleaning once stable)"))

    if not verbose_artifacts:
        if visible_pycache_dirs:
            issues.append(
                ToolIssue(
                    "warning",
                    f"Found {len(visible_pycache_dirs)} repo-visible __pycache__ directories (run clean to remove).",
                )
            )
        if visible_pyc_files:
            issues.append(
                ToolIssue("warning", f"Found {len(visible_pyc_files)} repo-visible .pyc files (run clean to remove).")
            )
        if visible_bak_files:
            issues.append(
                ToolIssue(
                    "warning",
                    f"Found {len(visible_bak_files)} repo-visible .bak files (consider cleaning once stable).",
                )
            )

    return issues


def _smoke_inline_build(repo_root: Path) -> Tuple[List[str], List[str]]:
    warnings, errors = _issues_to_legacy_lists(_smoke_inline_build_issues(repo_root))
    return warnings, errors


def _smoke_inline_build_issues(repo_root: Path) -> list[ToolIssue]:
    issues: list[ToolIssue] = []

    try:
        from scalpel.render.inline import build_html
    except Exception as e:
        issues.append(ToolIssue("error", f"Import failed: scalpel.render.inline.build_html ({e})"))
        return issues

    data: Dict[str, Any] = {
        "cfg": {
            "view_key": "smoke",
            "view_start_ms": 0,
            "days": 7,
            "px_per_min": 1.5,
            "work_start_min": 8 * 60,
            "work_end_min": 18 * 60,
            "snap_min": 5,
            "default_duration_min": 30,
            "max_infer_duration_min": 240,
        },
        "tasks": [],
        "meta": {"smoke": True},
    }

    try:
        html = build_html(data)
    except Exception as e:
        issues.append(ToolIssue("error", f"build_html(data) raised: {e}"))
        return issues

    if not isinstance(html, str) or len(html) < 500:
        issues.append(ToolIssue("error", "build_html returned an unexpectedly small result (HTML seems empty)"))
        return issues

    if "__DATA_JSON__" in html:
        issues.append(ToolIssue("error", "HTML still contains __DATA_JSON__ placeholder (template injection failed)"))
    if '"cfg"' not in html or '"tasks"' not in html:
        issues.append(
            ToolIssue("warning", 'HTML does not obviously contain "cfg"/"tasks" strings; template may have changed (verify manually)')
        )

    return issues


def _build_result(root: Path, *, strict: bool, verbose_artifacts: bool) -> ToolResult:
    issues: list[ToolIssue] = []
    issues.extend(_scan_tree_issues(root, verbose_artifacts=verbose_artifacts))
    issues.extend(_smoke_inline_build_issues(root))
    return result_from_issues(tool="scalpel-doctor", issues=issues, strict_warnings=strict)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scalpel.tools.doctor", description="Repository hygiene & smoke checks for scalpel.")
    ap.add_argument("--root", default="", help="Repo root (defaults to auto-detect from CWD).")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit code 2).")
    ap.add_argument("--verbose-artifacts", action="store_true", help="List every pycache/pyc/bak artifact.")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser() if args.root else _find_repo_root(Path.cwd())
    if not root:
        print("ERROR: Could not locate repo root (expected scalpel/__init__.py). Run with --root /path/to/repo", file=sys.stderr)
        return 2

    sys.path.insert(0, str(root))

    print(f"[scalpel-doctor] repo_root: {root}")
    print(f"[scalpel-doctor] python: {sys.executable}")

    result = _build_result(root, strict=bool(args.strict), verbose_artifacts=bool(args.verbose_artifacts))
    warnings = result.issues_for_level("warning")
    errors = result.issues_for_level("error")

    if errors:
        print("\n[scalpel-doctor] ERRORS:")
        for e in errors:
            print(f"  - {e.message}")
    if warnings:
        print("\n[scalpel-doctor] WARNINGS:")
        for w in warnings:
            print(f"  - {w.message}")

    if result.status == "fail" and warnings and not errors:
        print("\n[scalpel-doctor] RESULT: WARN (strict => FAIL)")
        return result.exit_code
    if result.status == "fail":
        print("\n[scalpel-doctor] RESULT: FAIL")
        return result.exit_code
    if result.status == "warn":
        print("\n[scalpel-doctor] RESULT: WARN")
        return result.exit_code
    print("\n[scalpel-doctor] RESULT: OK")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
