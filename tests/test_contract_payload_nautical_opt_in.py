from __future__ import annotations

import datetime as dt
import inspect
import json
import os
import unittest
from unittest.mock import patch

import scalpel.payload as payload_mod
from scalpel.process import CommandResult


class TestPayloadNauticalOptInContract(unittest.TestCase):
    def test_nautical_hooks_are_enabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(payload_mod._nautical_hooks_enabled())

    def test_explicit_disable_skips_home_probe(self) -> None:
        with patch("scalpel.payload.shutil.which", side_effect=AssertionError("disabled query must not probe PATH")):
            self.assertEqual(payload_mod._build_nautical_preview_tasks(
                base_tasks=[], raw_tasks=[], start_date=dt.date(2026, 1, 1), days=1,
                tz_name="UTC", default_duration_min=10, max_infer_duration_min=480,
                nautical_hooks_enabled=False,
            ), [])

    def test_env_can_disable_default(self) -> None:
        with patch.dict(os.environ, {"SCALPEL_ENABLE_NAUTICAL_HOOKS": "0"}, clear=False):
            self.assertFalse(payload_mod._nautical_hooks_enabled())

    def test_public_query_command_is_discovered_from_path(self) -> None:
        with patch("scalpel.payload.shutil.which", return_value="/usr/local/bin/nautical"):
            self.assertEqual(payload_mod._nautical_query_command(), ["/usr/local/bin/nautical", "query"])

    def test_occurrence_query_uses_public_json_command(self) -> None:
        response = {
            "status": "ok",
            "results": [
                {
                    "task": {"uuid": "u1"},
                    "occurrences": [{"utc": "20260102T080000Z", "source": "cp"}],
                }
            ],
        }
        with (
            patch("scalpel.payload._nautical_query_command", return_value=["nautical", "query"]),
            patch(
                "scalpel.payload.run_checked",
                return_value=CommandResult(
                    argv=("nautical", "query"), returncode=0, stdout=json.dumps(response), stderr=""
                ),
            ) as run,
        ):
            occurrences = payload_mod._query_nautical_occurrences(
                start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 1, 7)
            )

        self.assertEqual(occurrences["u1"][0]["utc"], "20260102T080000Z")
        run.assert_called_once_with(
            [
                "nautical", "query", "occurrences", "--all", "--from", "2026-01-01",
                "--to", "2026-01-07", "--omissions", "exclude",
            ],
            timeout_s=30.0,
        )

    def test_payload_does_not_import_nautical_internals(self) -> None:
        source = inspect.getsource(payload_mod)
        self.assertNotIn("nautical_core", source)
        self.assertNotIn("validate_anchor_expr_strict", source)

    def test_cp_previews_have_unique_uuids_with_multiple_same_day_spawns(self) -> None:
        raw_tasks = [
            {
                "uuid": "u1",
                "description": "Chain task",
                "cp": "PT2H",
                "chain": "on",
                "chainMax": 4,
                "link": 1,
            }
        ]
        base_due = int(dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        base_tasks = [
            {
                "uuid": "u1",
                "description": "Chain task",
                "due_ms": base_due,
                "scheduled_ms": None,
                "duration_min": 30,
            }
        ]

        occurrence_ms = int(dt.datetime(2026, 1, 2, 8, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        occurrences = {"u1": [{"utc": dt.datetime.fromtimestamp(occurrence_ms / 1000, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")} for _ in range(3)]}
        with patch("scalpel.payload._query_nautical_occurrences", return_value=occurrences):
            out = payload_mod._build_nautical_preview_tasks(
                base_tasks=base_tasks,
                raw_tasks=raw_tasks,
                start_date=dt.date(2026, 1, 1),
                days=2,
                tz_name="UTC",
                default_duration_min=30,
                max_infer_duration_min=480,
                nautical_hooks_enabled=True,
            )

        cp_previews = [t for t in out if t.get("nautical_kind") == "cp"]
        self.assertEqual(len(cp_previews), 3)
        self.assertEqual([t.get("nautical_link") for t in cp_previews], [0, 0, 0])
        self.assertEqual(len({str(t.get("uuid")) for t in cp_previews}), 3)
        self.assertEqual(
            [int(t.get("due_ms")) for t in cp_previews],
            sorted(int(t.get("due_ms")) for t in cp_previews),
        )

    def test_preview_builder_skips_loader_when_raw_tasks_have_no_nautical_fields(self) -> None:
        raw_tasks = [{"uuid": "u1", "description": "Normal task"}]
        base_tasks = [{"uuid": "u1", "due_ms": 1_700_000_000_000, "scheduled_ms": None, "duration_min": 30}]
        with patch("scalpel.payload._query_nautical_occurrences") as query_mod:
            out = payload_mod._build_nautical_preview_tasks(
                base_tasks=base_tasks,
                raw_tasks=raw_tasks,
                start_date=dt.date(2026, 1, 1),
                days=7,
                tz_name="UTC",
                default_duration_min=30,
                max_infer_duration_min=480,
                nautical_hooks_enabled=True,
            )
        self.assertEqual(out, [])
        query_mod.assert_not_called()

    def test_preview_builder_skips_completed_source_tasks(self) -> None:
        base_ms = int(dt.datetime(2026, 1, 1, 8, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        raw_tasks = [
            {
                "uuid": "done-1",
                "description": "Completed source",
                "status": "completed",
                "anchor": "tomorrow@09",
                "cp": "PT1D",
                "chain": "on",
                "chainMax": 3,
                "link": 1,
                "end": "20260101T080000Z",
            }
        ]
        base_tasks = [
            {
                "uuid": "done-1",
                "description": "Completed source",
                "status": "completed",
                "due_ms": base_ms,
                "end_ms": base_ms,
                "completed_end_ms": base_ms,
                "scheduled_ms": None,
                "duration_min": 30,
            }
        ]

        with patch("scalpel.payload._query_nautical_occurrences", side_effect=AssertionError("completed tasks must not query")):
            out = payload_mod._build_nautical_preview_tasks(
                base_tasks=base_tasks,
                raw_tasks=raw_tasks,
                start_date=dt.date(2026, 1, 1),
                days=7,
                tz_name="UTC",
                default_duration_min=30,
                max_infer_duration_min=480,
                nautical_hooks_enabled=True,
            )

        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
