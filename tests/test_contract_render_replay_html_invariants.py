# Contract: render/replay HTML invariants (golden payload -> replay HTML)
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from scalpel.schema import LATEST_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


def _extract_embedded_json_from_html(html: str) -> dict:
    """
    Extract the first <script ... type="application/json">...</script> block
    and parse it as JSON.
    """
    m = re.search(
        r'<script\b[^>]*type="application/json"[^>]*>\s*(.*?)\s*</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise AssertionError("No <script type='application/json'> block found in replay HTML.")

    raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Embedded JSON could not be parsed: {e}") from e


class TestRenderReplayHtmlInvariantsContract(unittest.TestCase):
    def test_replay_html_round_trips_payload_and_has_invariants(self) -> None:
        self.assertTrue(FIXTURE.exists(), f"Missing fixture: {FIXTURE}")
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

        # Render using the library template (render path) – no smoke builder involved.
        from scalpel.render.template import build_html

        html = build_html(payload)

        # Basic shell invariants (stable, low noise)
        self.assertTrue(html.lstrip().lower().startswith("<!doctype html>"), "Missing <!doctype html>.")
        self.assertIn("<html", html.lower())
        self.assertIn("</html>", html.lower())

        # Template placeholders must never leak.
        for ph in ("__CSS_BLOCK__", "__JS_BLOCK__", "__BODY_MARKUP__", "__DATA_JSON__"):
            self.assertNotIn(ph, html, f"Template placeholder leaked: {ph}")

        # Replay must include a JSON payload script tag.
        # (We keep the extraction robust to ID/name changes, but still require JSON.)
        embedded = _extract_embedded_json_from_html(html)

        # Contract: render does not mutate payload.
        self.assertEqual(embedded, payload, "Replay HTML embedded payload differs from golden payload fixture.")

        # Contract: schema invariants exist and are stable.
        # self.assertEqual(embedded.get("schema_version"), LATEST_SCHEMA_VERSION, "")
        meta = embedded.get("meta") or {}
        self.assertIsInstance(meta, dict)
        self.assertIn("generated_at", meta)
        self.assertIn("generated_by", meta)
        self.assertIn("start_ymd", meta)

        # Sanity: known synthetic content is present (string appears inside embedded JSON).
        self.assertIn("SMOKE: Planned task", html, "Expected synthetic SMOKE task marker missing from replay HTML.")

        # Discoverability UX invariants: help + quick command entry points exist.
        for id_ in ("btnCommand", "btnHelp", "pendingMeta", "cmdGuide", "toast", "helpModal", "commandModal", "commandQ"):
            n = html.count(f'id="{id_}"')
            self.assertEqual(n, 1, f"expected id={id_!r} once, found {n}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
