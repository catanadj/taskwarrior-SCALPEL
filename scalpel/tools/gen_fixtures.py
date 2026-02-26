
"""Generate and/or check golden fixtures.

Fixtures:
  - tests/fixtures/golden_payload_v1.json
  - tests/fixtures/golden_payload_v2.json

Modes:
  --check   (default) exit non-zero if any selected fixture differs from generated output
  --write            overwrite selected fixture(s) to match current generator output

Design:
  - Uses scalpel.tools.smoke_build with fixed --start/--days to be deterministic.
  - Normalizes volatile fields (e.g. generated_at) to avoid churn.
  - Generates v2 by upgrading the deterministic v1 smoke payload via scalpel.schema.upgrade_payload
    (with best-effort signature compatibility).
"""

from __future__ import annotations
from scalpel.schema import LATEST_SCHEMA_VERSION, upgrade_payload
import argparse
import copy
import difflib
import importlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

GEN_START = "2020-01-01"
GEN_DAYS = 7

FIXTURES: Dict[int, Path] = {
    1: Path("tests/fixtures/golden_payload_v1.json"),
    2: Path("tests/fixtures/golden_payload_v2.json"),
}


def _repo_root() -> Path:
    # Expected location: <repo>/scalpel/tools/gen_fixtures.py  -> parents[2] == <repo>
    return Path(__file__).resolve().parents[2]


def _canonical(payload: Dict[str, Any]) -> str:
    # Stable text representation for diffs and git review.
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _normalize(obj: Any) -> Any:
    """Recursively normalize volatile fields so fixtures don't churn."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k == "generated_at":
                out[k] = "1970-01-01T00:00:00Z"
            else:
                out[k] = _normalize(v)
        return out
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    return obj


def _build_smoke_payload_v1(repo: Path) -> Dict[str, Any]:
    """Run smoke_build deterministically and capture the JSON payload it emits."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out_html = td / "smoke.html"
        out_json = td / "payload.json"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo)

        env["TZ"] = "UTC"  # deterministic fixtures across machines
        env["SCALPEL_TZ"] = "UTC"
        env["SCALPEL_DISPLAY_TZ"] = "local"
        cmd = [
            sys.executable,
            "-m",
            "scalpel.tools.smoke_build",
            "--out",
            str(out_html),
            "--out-json",
            str(out_json),
            "--strict",
            "--schema",
            "1",
            "--tz",
            "UTC",
            "--display-tz",
            "local",
            "--start",
            GEN_START,
            "--days",
            str(GEN_DAYS),
        ]
        subprocess.run(cmd, cwd=str(repo), env=env, check=True)

        raw = json.loads(out_json.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            raise SystemExit("smoke_build --out-json must produce an object/dict")
        return raw


def _import_upgrade_payload(repo: Path):
    """Import scalpel.schema.upgrade_payload with repo-root on sys.path."""
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    mod = importlib.import_module("scalpel.schema")
    fn = getattr(mod, "upgrade_payload", None)
    if not callable(fn):
        raise SystemExit("scalpel.schema.upgrade_payload not found or not callable")
    return fn


def _upgrade_to_version(repo: Path, payload: Dict[str, Any], target_version: int) -> Dict[str, Any]:
    """Upgrade payload to target schema version (best-effort across signatures)."""
    upgrade_payload_fn = _import_upgrade_payload(repo)

    p = copy.deepcopy(payload)
    sig = inspect.signature(upgrade_payload_fn)

    # Try common parameter names used in prior iterations.
    kwargs: Dict[str, Any] = {}
    for name in ("target_version", "to_version", "schema_version", "version"):
        if name in sig.parameters:
            kwargs[name] = target_version
            break

    res = upgrade_payload_fn(p, **kwargs)  # may mutate in place or return a dict
    out = res if isinstance(res, dict) else p

    # Enforce requested target when possible (makes failures loud).
    got = out.get("schema_version")
    if got != target_version:
        raise SystemExit(f"upgrade_payload did not produce schema_version={target_version} (got {got!r})")
    return out


def _diff(old_txt: str, new_txt: str, fixture_rel: Path) -> str:
    return "".join(
        difflib.unified_diff(
            old_txt.splitlines(True),
            new_txt.splitlines(True),
            fromfile=str(fixture_rel),
            tofile=str(fixture_rel),
            lineterm="",
        )
    )


def _write_or_check_one(
    *,
    repo: Path,
    fixture_rel: Path,
    payload: Dict[str, Any],
    write: bool,
) -> Tuple[bool, str]:
    """Return (ok, message)."""
    fixture_path = repo / fixture_rel
    fixture_path.parent.mkdir(parents=True, exist_ok=True)

    new_obj = _normalize(payload)
    new_txt = _canonical(new_obj)

    old_txt = fixture_path.read_text(encoding="utf-8", errors="replace") if fixture_path.exists() else ""
    if old_txt == new_txt:
        return True, f"[scalpel-fixtures] OK: {fixture_rel} up to date"

    d = _diff(old_txt, new_txt, fixture_rel)

    if write:
        fixture_path.write_text(new_txt, encoding="utf-8", newline="\n")
        msg = f"[scalpel-fixtures] WROTE: {fixture_rel}"
        if d.strip():
            msg += "\n" + d
        return True, msg

    msg = f"[scalpel-fixtures] FAIL: {fixture_rel} differs from generated output"
    if d.strip():
        msg += "\n" + d
    return False, msg


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="scalpel-gen-fixtures",
        description="Generate/check SCALPEL golden fixtures (v1/v2).",
    )
    mx = ap.add_mutually_exclusive_group()
    mx.add_argument("--check", action="store_true", help="Check fixture(s) (default)")
    mx.add_argument("--write", action="store_true", help="Write fixture(s) if changed")
    ap.add_argument(
        "--schema",
        type=int,
        default=LATEST_SCHEMA_VERSION,
        help="Generate/check fixtures up to this schema version (default: latest supported).",
    )

    ns = ap.parse_args(argv)
    # SCALPEL_SCHEMA_SELECT_4_1
    # Schema selection: default to latest; never downgrade input.
    _req_schema = getattr(ns, 'schema', None)
    try:
        _req_schema_i = int(_req_schema) if _req_schema is not None else int(LATEST_SCHEMA_VERSION)
    except Exception:
        _req_schema_i = int(LATEST_SCHEMA_VERSION)
    if _req_schema_i < 1:
        _req_schema_i = 1
    if _req_schema_i > int(LATEST_SCHEMA_VERSION):
        # Keep error text consistent across tools.
        raise SystemExit(f"--schema {_req_schema_i} unsupported (latest={LATEST_SCHEMA_VERSION})")
    do_write = bool(ns.write)
    schema_max = _req_schema_i  # validated above

    repo = _repo_root()

    # Always build the deterministic base payload via smoke_build.
    base_v1 = _build_smoke_payload_v1(repo)

    # Build payloads up to schema_max.
    targets: List[Tuple[int, Dict[str, Any]]] = [(1, base_v1)]
    if schema_max >= 2:
        v2 = _upgrade_to_version(repo, base_v1, 2)
        targets.append((2, v2))

    any_fail = False
    for ver, payload in targets:
        fixture_rel = FIXTURES[ver]
        ok, msg = _write_or_check_one(repo=repo, fixture_rel=fixture_rel, payload=payload, write=do_write)
        print(msg)
        any_fail = any_fail or (not ok)

    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
