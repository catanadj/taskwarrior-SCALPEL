from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


class TestFilterPayloadToolContract:
    def test_filter_payload_tool_by_uuid(self, tmp_path: Path):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        tasks = payload.get("tasks") or []
        assert isinstance(tasks, list) and tasks, "golden fixture has no tasks"
        first = tasks[0]
        assert isinstance(first, dict)
        u = first.get("uuid")
        assert isinstance(u, str) and u

        out_json = tmp_path / "filtered.json"
        cmd = [sys.executable, "-m", "scalpel.tools.filter_payload", "--in", str(FIXTURE), "--q", f"uuid:{u}", "--out", str(out_json)]
        p = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
        combined = (p.stdout or "") + "\n" + (p.stderr or "")
        assert p.returncode == 0, combined

        out = json.loads(out_json.read_text(encoding="utf-8"))
        assert isinstance(out, dict)
        out_tasks = out.get("tasks") or []
        assert isinstance(out_tasks, list)
        assert len(out_tasks) == 1
        assert out_tasks[0].get("uuid") == u

        # Must still have indices dict with required keys
        idx = out.get("indices")
        assert isinstance(idx, dict)
        for k in ("by_uuid", "by_status", "by_project", "by_tag", "by_day"):
            assert k in idx, f"missing indices.{k}"
