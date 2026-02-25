from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
