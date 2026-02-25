from __future__ import annotations

import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "scalpel" / "__init__.py").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _scan_tree(root: Path, *, verbose_artifacts: bool = False) -> Tuple[List[str], List[str]]:
    """Scan the repository for common hygiene issues.

    Keep this relatively conservative: focus on artifacts that tend to break
    releases (patch rejects, copy artifacts, bytecode) while avoiding deep
    semantic checks.
    """

    warnings: List[str] = []
    errors: List[str] = []

    bad_name = re.compile(r"^Copy \(\d+\) ")
    skip_dirs = {".git", "build", "dist", ".venv", ".mypy_cache", ".pytest_cache"}
    pycache_count = 0
    pyc_count = 0
    bak_count = 0

    for p in root.rglob("*"):
        # Skip common generated directories.
        if any(part in skip_dirs for part in p.parts):
            continue

        if p.is_dir():
            if p.name == "__pycache__":
                pycache_count += 1
                if verbose_artifacts:
                    warnings.append(f"Found __pycache__ directory: {p.relative_to(root)} (consider cleaning it)")
            continue

        name = p.name
        rel = str(p.relative_to(root))

        if bad_name.search(name):
            errors.append(f"Stray copy artifact: {rel}")
        if name.endswith(".rej"):
            errors.append(f"Patch reject present: {rel}")
        if name.endswith(".orig"):
            errors.append(f"Patch artifact present: {rel}")

        if name.endswith(".pyc"):
            pyc_count += 1
            if verbose_artifacts:
                warnings.append(f"Bytecode file present: {rel} (consider cleaning)")
        if name.endswith(".bak"):
            bak_count += 1
            if verbose_artifacts:
                warnings.append(f"Backup file present: {rel} (ok, but consider cleaning once stable)")

    if not verbose_artifacts:
        if pycache_count:
            warnings.append(f"Found {pycache_count} __pycache__ directories (run clean to remove).")
        if pyc_count:
            warnings.append(f"Found {pyc_count} .pyc files (run clean to remove).")
        if bak_count:
            warnings.append(f"Found {bak_count} .bak files (consider cleaning once stable).")

    return warnings, errors


def _smoke_inline_build(repo_root: Path) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    errors: List[str] = []

    try:
        from scalpel.render.inline import build_html  # type: ignore
    except Exception as e:
        errors.append(f"Import failed: scalpel.render.inline.build_html ({e})")
        return warnings, errors

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
        errors.append(f"build_html(data) raised: {e}")
        return warnings, errors

    if not isinstance(html, str) or len(html) < 500:
        errors.append("build_html returned an unexpectedly small result (HTML seems empty)")
        return warnings, errors

    if "__DATA_JSON__" in html:
        errors.append("HTML still contains __DATA_JSON__ placeholder (template injection failed)")
    if '"cfg"' not in html or '"tasks"' not in html:
        warnings.append('HTML does not obviously contain "cfg"/"tasks" strings; template may have changed (verify manually)')

    return warnings, errors


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

    warnings: List[str] = []
    errors: List[str] = []

    w1, e1 = _scan_tree(root, verbose_artifacts=bool(args.verbose_artifacts))
    warnings += w1
    errors += e1

    w2, e2 = _smoke_inline_build(root)
    warnings += w2
    errors += e2

    if errors:
        print("\n[scalpel-doctor] ERRORS:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("\n[scalpel-doctor] WARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("\n[scalpel-doctor] RESULT: FAIL")
        return 2
    if warnings and args.strict:
        print("\n[scalpel-doctor] RESULT: WARN (strict => FAIL)")
        return 2
    if warnings:
        print("\n[scalpel-doctor] RESULT: WARN")
        return 1
    print("\n[scalpel-doctor] RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
