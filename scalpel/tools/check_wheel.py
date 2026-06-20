from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from scalpel.render.inline_css import CSS_ASSET_PATHS
from scalpel.render.inline_js import JS_ASSET_PATHS


def validate_wheel(path: Path) -> list[str]:
    """Return packaging errors for a built wheel."""
    if not path.is_file():
        return [f"wheel does not exist: {path}"]

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile) as ex:
        return [f"invalid wheel archive: {ex}"]

    required = {
        *(f"scalpel/render/{asset}" for asset in CSS_ASSET_PATHS),
        *(f"scalpel/render/{asset}" for asset in JS_ASSET_PATHS),
        "scalpel/render/js/persist.js",
    }
    missing = sorted(required - names)
    stale_wrappers = sorted(
        name
        for name in names
        if name.startswith(("scalpel/render/css/part", "scalpel/render/js/part")) and name.endswith(".py")
    )
    if "scalpel/render/js/persist.py" in names:
        stale_wrappers.append("scalpel/render/js/persist.py")

    errors = [f"missing packaged asset: {name}" for name in missing]
    errors.extend(f"obsolete frontend wrapper packaged: {name}" for name in stale_wrappers)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate packaged SCALPEL wheel contents.")
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)

    errors = validate_wheel(args.wheel)
    if errors:
        for error in errors:
            print(f"[scalpel-wheel] ERROR: {error}")
        return 2
    print(f"[scalpel-wheel] OK: {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
