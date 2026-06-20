from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from scalpel.render.assets import read_render_asset
from scalpel.render.inline_js import JS_ASSET_PATHS, JS_BLOCK

STANDALONE_JS_ASSET_PATHS = ("js/persist.js",)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Syntax-check SCALPEL JavaScript assets and assembled bundle.")
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
        targets = [(path, read_render_asset(path)) for path in STANDALONE_JS_ASSET_PATHS]
        targets.append((f"assembled bundle ({len(JS_ASSET_PATHS)} ordered fragments)", JS_BLOCK))
        for index, (label, source) in enumerate(targets):
            target = Path(tmp) / f"{index:02d}.js"
            target.write_text(source, encoding="utf-8")
            checked = subprocess.run([node, "--check", str(target)], check=False, text=True)
            if checked.returncode != 0:
                print(f"[scalpel-frontend] ERROR: invalid JavaScript in {label}")
                return checked.returncode
    print(f"[scalpel-frontend] OK: {len(JS_ASSET_PATHS)} fragments, standalone assets, and assembled bundle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
