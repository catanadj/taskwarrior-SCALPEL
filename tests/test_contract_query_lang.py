# SCALPEL_QUERY_LANG_V2
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scalpel.query_lang import Query


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_payload_v1.json"


def _load_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _pick_task(payload: dict) -> dict:
    for t in payload.get("tasks") or []:
        if isinstance(t, dict) and isinstance(t.get("uuid"), str) and t.get("uuid"):
            return t
    raise AssertionError("Fixture has no task with uuid")


def _pick_task_with_tag(payload: dict) -> tuple[dict, str] | None:
    for t in payload.get("tasks") or []:
        if isinstance(t, dict) and isinstance(t.get("uuid"), str) and t.get("uuid"):
            tags = t.get("tags")
            if isinstance(tags, list):
                for x in tags:
                    if isinstance(x, str) and x:
                        return (t, x)
    return None


def _pick_task_with_project(payload: dict) -> tuple[dict, str] | None:
    for t in payload.get("tasks") or []:
        if isinstance(t, dict) and isinstance(t.get("uuid"), str) and t.get("uuid"):
            pr = t.get("project")
            if isinstance(pr, str) and pr:
                return (t, pr)
    return None


def _pick_desc_word(t: dict) -> str | None:
    d = t.get("description")
    if not isinstance(d, str) or not d:
        return None
    for w in re.split(r"\W+", d):
        if len(w) >= 4:
            return w
    return None


class TestQueryLangContract(unittest.TestCase):
    def test_uuid_query_finds_task(self):
        payload = _load_payload()
        t = _pick_task(payload)
        u = t["uuid"]
        res = Query.parse(f"uuid:{u}").run(payload)
        self.assertTrue(any(x.get("uuid") == u for x in res))

    def test_project_and_minus_tag_shorthand_when_available(self):
        payload = _load_payload()
        picked = _pick_task_with_project(payload)
        picked2 = _pick_task_with_tag(payload)
        if not picked or not picked2:
            self.skipTest("Fixture lacks project or tags for this contract")
        t, pr = picked
        _, tg = picked2
        # Taskwarrior style: project:work -blocked (exclude tag)
        q = Query.parse(f"project:{pr} -{tg}")
        res = q.run(payload)
        # result should contain only tasks from project and not having tg
        for x in res:
            self.assertEqual(x.get("project"), pr)
            self.assertTrue(tg not in (x.get("tags") or []))

    def test_description_regex_include_and_exclude(self):
        payload = _load_payload()
        t = _pick_task(payload)
        u = t["uuid"]
        w = _pick_desc_word(t)
        if not w:
            self.skipTest("No description word available")
        # include regex should keep the task
        res_inc = Query.parse(f"uuid:{u} description~{w}").run(payload)
        self.assertTrue(any(x.get("uuid") == u for x in res_inc))
        # exclude regex should remove the task
        res_exc = Query.parse(f"uuid:{u} desc!~{w}").run(payload)
        self.assertFalse(any(x.get("uuid") == u for x in res_exc))

    def test_bare_token_is_description_substring(self):
        payload = _load_payload()
        t = _pick_task(payload)
        u = t["uuid"]
        w = _pick_desc_word(t)
        if not w:
            self.skipTest("No description word available")
        res = Query.parse(f"uuid:{u} {w}").run(payload)
        self.assertTrue(any(x.get("uuid") == u for x in res))



    def test_desc_regex_preserves_backslashes(self):
        payload = {
            "schema_version": 1,
            "cfg": {},
            "generated_at": "2020-01-01T00:00:00Z",
            "tasks": [
                {"uuid": "u1", "status": "pending", "tags": [], "description": "A [x]"},
                {"uuid": "u2", "status": "pending", "tags": [], "description": "B x"},
            ],
            "indices": {
                "by_uuid": {"u1": 0, "u2": 1},
                "by_status": {},
                "by_project": {},
                "by_tag": {},
                "by_day": {},
            },
        }

        q_in = Query.parse(r"desc~\\[")
        got_in = {t.get("uuid") for t in q_in.run(payload)}
        self.assertEqual(got_in, {"u1"})

        q_out = Query.parse(r"desc!~\\[")
        got_out = {t.get("uuid") for t in q_out.run(payload)}
        self.assertEqual(got_out, {"u2"})
if __name__ == "__main__":
    unittest.main(verbosity=2)
