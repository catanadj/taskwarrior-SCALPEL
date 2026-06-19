from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from scalpel.render.inline_js import JS_BLOCK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Syntax-check the assembled SCALPEL JavaScript bundle.")
    parser.add_argument("--require-node", action="store_true")
    args = parser.parse_args(argv)

    node = shutil.which("node")
    if node is None:
        if args.require_node:
            print("[scalpel-frontend] ERROR: node is required")
            return 2
        print("[scalpel-frontend] WARN: node not found; JavaScript syntax check skipped")
        return 0

    with tempfile.TemporaryDirectory(prefix="scalpel-frontend-") as tmp:
        bundle = Path(tmp) / "scalpel-bundle.js"
        bundle.write_text(JS_BLOCK, encoding="utf-8")
        checked = subprocess.run([node, "--check", str(bundle)], check=False, text=True)
    if checked.returncode != 0:
        return checked.returncode
    print("[scalpel-frontend] OK: assembled JavaScript syntax")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
