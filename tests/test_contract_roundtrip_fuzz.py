\
from __future__ import annotations

import json
import os
import random
import re
import tempfile
import unittest
from pathlib import Path

from scalpel.html_extract import extract_payload_json_from_html_file
from scalpel.validate import assert_valid_payload

# Repo root = tests/.. (this file lives in tests/)
REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


def _canon(obj) -> str:
    # Canonical JSON for stable comparisons
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _load_fixture() -> dict:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("golden_payload_v1.json must be a JSON object")
    return payload


def _render_replay_html(payload: dict) -> str:
    # Prefer the same builder used by tools; this should remain stable.
    from scalpel.render.inline import build_html  # noqa: WPS433

    return build_html(payload)


def _mutate_tw_data_script_tag(html: str, rng: random.Random) -> str:
    # Make harmless variations to the <script id="tw-data" ...> opening tag.
    # Keep id="tw-data" present so the extractor still finds it.
    m = re.search(r"(?is)<script[^>]*\\bid=[\"']tw-data[\"'][^>]*>", html)
    if not m:
        return html

    tag = m.group(0)
    attrs = [
        ("type", "application/json"),
        ("id", "tw-data"),
        ("data-fuzz", str(rng.randint(1, 9))),
    ]

    # randomize quote styles and attr order
    rng.shuffle(attrs)
    pieces = []
    for k, v in attrs:
        q = "'" if rng.random() < 0.5 else '"'
        pieces.append(f"{k}={q}{v}{q}")

    # optional extra whitespace
    ws1 = " " * rng.randint(1, 3)
    ws2 = " " * rng.randint(0, 2)
    new_tag = "<script" + ws1 + (ws2.join(pieces)) + ">"

    return html[: m.start()] + new_tag + html[m.end() :]


def _wrap_as_data_assignment(payload: dict, rng: random.Random) -> str:
    # Exercise the fallback extractor path: DATA = {...};
    blob = json.dumps(payload, ensure_ascii=False, indent=None)
    decl = rng.choice(["const", "var", ""])
    pad = " " * rng.randint(0, 3)
    return (
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        "<script>"
        f"{decl}{pad}DATA{pad}={pad}{blob}{pad};"
        "</script>"
        "</body></html>"
    )


class TestRoundTripHtmlExtractionFuzzContract(unittest.TestCase):
    def test_round_trip_replay_html_extracts_identical_payload(self):
        payload = _load_fixture()
        html = _render_replay_html(payload)

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "replay.html"
            p.write_text(html, encoding="utf-8")

            got = extract_payload_json_from_html_file(p)
            assert_valid_payload(got)
            self.assertEqual(_canon(got), _canon(payload))

    def test_fuzz_html_variants_keep_extraction_stable(self):
        iters = int(os.environ.get("SCALPEL_FUZZ_ITERS", "12"))
        seed = int(os.environ.get("SCALPEL_FUZZ_SEED", "1337"))
        rng = random.Random(seed)

        payload = _load_fixture()
        base_html = _render_replay_html(payload)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)

            for i in range(iters):
                mode = rng.choice(["tw-data", "data-assign"])
                if mode == "tw-data":
                    html = _mutate_tw_data_script_tag(base_html, rng)
                    # random whitespace around script body
                    html = re.sub(r"(?is)(<script[^>]*\\bid=[\"']tw-data[\"'][^>]*>)(\\s*)",
                                 r"\\1\\n\\n", html, count=1)
                else:
                    html = _wrap_as_data_assignment(payload, rng)

                p = td / f"case_{i:02d}.html"
                p.write_text(html, encoding="utf-8")

                got = extract_payload_json_from_html_file(p)
                assert_valid_payload(got)
                self.assertEqual(_canon(got), _canon(payload), f"mismatch in {p.name} mode={mode}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
