#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import stat
from datetime import datetime
from pathlib import Path


HOOK_BODY = '''#!/usr/bin/env bash
set -euo pipefail

# SCALPEL pre-commit gate (contracts)
#
# Bypass options:
#   - git commit --no-verify
#   - SCALPEL_SKIP_PRECOMMIT=1 git commit -m "..."
#
if [[ "${SCALPEL_SKIP_PRECOMMIT:-0}" == "1" ]]; then
  exit 0
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT" ]]; then
  exit 0
fi

cd "$ROOT"

# Prefer dev entrypoint if present.
if [[ -x "./scripts/scalpel_dev.sh" ]]; then
  echo "[pre-commit] scalpel contracts: ./scripts/scalpel_dev.sh test"
  ./scripts/scalpel_dev.sh test
  exit $?
fi

# Fallback: legacy wrapper.
if [[ -x "./scripts/scalpel_test_contract.sh" ]]; then
  echo "[pre-commit] scalpel contracts: ./scripts/scalpel_test_contract.sh"
  ./scripts/scalpel_test_contract.sh
  exit $?
fi

# Fallback: discover contract tests directly.
PY="${PYTHON:-python3}"
echo "[pre-commit] scalpel contracts: python -m unittest discover -s tests -p 'test_contract_*.py'"
"$PY" -m unittest discover -s tests -p "test_contract_*.py"
'''


def _git_root() -> Path | None:
    try:
        out = os.popen("git rev-parse --show-toplevel 2>/dev/null").read().strip()
        if not out:
            return None
        p = Path(out)
        return p if p.exists() else None
    except Exception:
        return None


def _hooks_dir(root: Path) -> Path:
    # Most repos: .git/hooks. We keep it simple and target that.
    return root / ".git" / "hooks"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="install_pre_commit_hook.py")
    ap.add_argument("--force", action="store_true", help="Overwrite existing pre-commit hook (still creates a backup).")
    ap.add_argument("--uninstall", action="store_true", help="Remove the pre-commit hook (backs it up if present).")
    ap.add_argument("--print", dest="do_print", action="store_true", help="Print hook body to stdout and exit.")
    ns = ap.parse_args(argv)

    if ns.do_print:
        print(HOOK_BODY.rstrip("\n"))
        return 0

    root = _git_root()
    if not root:
        print("[install-pre-commit] ERROR: not inside a git repo.")
        return 2

    hooks = _hooks_dir(root)
    hooks.mkdir(parents=True, exist_ok=True)

    hook_path = hooks / "pre-commit"
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    if ns.uninstall:
        if hook_path.exists():
            backup = hooks / f"pre-commit.{tag}.bak"
            backup.write_bytes(hook_path.read_bytes())
            hook_path.unlink()
            print(f"[install-pre-commit] Uninstalled: {hook_path}")
            print(f"[install-pre-commit] Backup:      {backup}")
        else:
            print("[install-pre-commit] No pre-commit hook installed.")
        return 0

    if hook_path.exists() and not ns.force:
        print(f"[install-pre-commit] ERROR: hook already exists: {hook_path}")
        print("[install-pre-commit] Use --force to overwrite (a backup will be created).")
        return 2

    if hook_path.exists():
        backup = hooks / f"pre-commit.{tag}.bak"
        backup.write_bytes(hook_path.read_bytes())
        print(f"[install-pre-commit] Backed up existing hook to: {backup}")

    hook_path.write_text(HOOK_BODY, encoding="utf-8", newline="\n")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"[install-pre-commit] Installed: {hook_path}")
    print("[install-pre-commit] Bypass: SCALPEL_SKIP_PRECOMMIT=1 git commit ...  (or git commit --no-verify)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
