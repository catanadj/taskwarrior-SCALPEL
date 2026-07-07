from __future__ import annotations

import datetime as dt
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scalpel.payload as payload_mod


class TestPayloadNauticalOptInContract(unittest.TestCase):
    def test_nautical_hooks_are_enabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(payload_mod._nautical_hooks_enabled())

    def test_explicit_disable_skips_home_probe(self) -> None:
        with patch("scalpel.payload.Path.home", side_effect=AssertionError("should not probe home paths")):
            mod = payload_mod._load_nautical_core(enabled=False)
        self.assertIsNone(mod)

    def test_env_can_disable_default(self) -> None:
        with patch.dict(os.environ, {"SCALPEL_ENABLE_NAUTICAL_HOOKS": "0"}, clear=False):
            self.assertFalse(payload_mod._nautical_hooks_enabled())

    def test_broken_nautical_core_in_home_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            task_dir = home / ".task"
            task_dir.mkdir(parents=True, exist_ok=True)
            (task_dir / "nautical_core.py").write_text("def broken(:\n", encoding="utf-8")

            with patch("scalpel.payload.Path.home", return_value=home), patch("scalpel.payload.eprint") as ep:
                mod = payload_mod._load_nautical_core(enabled=True)

            self.assertIsNone(mod)
            combined = "\n".join(str(c.args[0]) for c in ep.call_args_list if c.args)
            self.assertIn("WARN: failed loading nautical_core", combined)

    def test_home_package_is_preferred_over_legacy_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            task_dir = home / ".task"
            pkg_dir = task_dir / "nautical_core"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "__init__.py").write_text("SOURCE = 'package'\n", encoding="utf-8")
            (task_dir / "nautical_core.py").write_text("SOURCE = 'pyfile'\n", encoding="utf-8")

            with patch("scalpel.payload.Path.home", return_value=home):
                mod = payload_mod._load_nautical_core(enabled=True)

            self.assertIsNotNone(mod)
            self.assertEqual(getattr(mod, "SOURCE", None), "package")

    def test_home_package_is_preferred_over_generic_import(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            task_dir = home / ".task"
            pkg_dir = task_dir / "nautical_core"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "__init__.py").write_text("SOURCE = 'package'\n", encoding="utf-8")

            real_import_module = payload_mod.importlib.import_module

            def fake_import_module(name: str, package: str | None = None):
                if name == "nautical_core":
                    raise AssertionError("generic import should not run before home package")
                return real_import_module(name, package)

            with (
                patch("scalpel.payload.Path.home", return_value=home),
                patch("scalpel.payload.importlib.import_module", side_effect=fake_import_module),
            ):
                mod = payload_mod._load_nautical_core(enabled=True)

            self.assertIsNotNone(mod)
            self.assertEqual(getattr(mod, "SOURCE", None), "package")

    def test_cp_previews_have_unique_uuids_with_multiple_same_day_spawns(self) -> None:
        class FakeNautical:
            @staticmethod
            def parse_cp_duration(cp_str: str):
                if cp_str != "PT2H":
                    return None
                return dt.timedelta(hours=2)

            @staticmethod
            def coerce_int(value, default: int):
                try:
                    return int(value)
                except Exception:
                    return default

            @staticmethod
            def parse_dt_any(_value: str):
                return None

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

        with patch("scalpel.payload._load_nautical_core", return_value=FakeNautical()):
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
        self.assertEqual([t.get("nautical_link") for t in cp_previews], [2, 3, 4])
        self.assertEqual(len({str(t.get("uuid")) for t in cp_previews}), 3)
        self.assertEqual(
            [int(t.get("due_ms")) for t in cp_previews],
            sorted(int(t.get("due_ms")) for t in cp_previews),
        )

    def test_preview_builder_skips_loader_when_raw_tasks_have_no_nautical_fields(self) -> None:
        raw_tasks = [{"uuid": "u1", "description": "Normal task"}]
        base_tasks = [{"uuid": "u1", "due_ms": 1_700_000_000_000, "scheduled_ms": None, "duration_min": 30}]
        with patch("scalpel.payload._load_nautical_core") as load_mod:
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
        load_mod.assert_not_called()

    def test_preview_builder_skips_completed_source_tasks(self) -> None:
        class FakeNautical:
            DEFAULT_DUE_HOUR = 11

            @staticmethod
            def validate_anchor_expr_strict(_anchor: str):
                return [[{"mods": {"t": "09:00"}}]]

            @staticmethod
            def anchors_between_expr(_dnf, start_excl, end_excl, *, default_seed, seed_base):
                del start_excl, end_excl, default_seed, seed_base
                return [dt.date(2026, 1, 2)]

            @staticmethod
            def atom_matches_on(_atom, _target, _seed_date):
                return True

            @staticmethod
            def pick_hhmm_from_dnf_for_date(_dnf, _date, _seed_date):
                return "09:00"

            @staticmethod
            def parse_cp_duration(cp_str: str):
                if cp_str != "PT1D":
                    return None
                return dt.timedelta(days=1)

            @staticmethod
            def coerce_int(value, default: int):
                try:
                    return int(value)
                except Exception:
                    return default

            @staticmethod
            def parse_dt_any(_value: str):
                return None

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

        with patch("scalpel.payload._load_nautical_core", return_value=FakeNautical()):
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
