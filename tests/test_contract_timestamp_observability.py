from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scalpel.normalize import normalize_task


class TestTimestampObservabilityContract(unittest.TestCase):
    def test_invalid_timestamp_logs_warning_when_obs_enabled(self) -> None:
        task = {"uuid": "u1", "description": "x", "due": "20251301T000000Z"}
        with patch.dict(os.environ, {"SCALPEL_OBS_LOG": "1"}, clear=False), patch("scalpel.normalize.eprint") as ep:
            out = normalize_task(task)
        self.assertIsNotNone(out)
        combined = "\n".join(str(c.args[0]) for c in ep.call_args_list if c.args)
        self.assertIn("[scalpel.normalize] WARN: invalid due timestamp", combined)

    def test_invalid_timestamp_does_not_log_when_obs_disabled(self) -> None:
        task = {"uuid": "u1", "description": "x", "due": "20251301T000000Z"}
        with patch.dict(os.environ, {}, clear=True), patch("scalpel.normalize.eprint") as ep:
            out = normalize_task(task)
        self.assertIsNotNone(out)
        self.assertFalse(ep.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
