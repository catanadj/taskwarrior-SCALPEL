from __future__ import annotations

import unittest
from unittest.mock import patch

from scalpel.payload import _warn_nautical_disabled_if_needed


class TestPayloadNauticalWarningContract(unittest.TestCase):
    def test_warns_when_nautical_fields_present_and_disabled(self) -> None:
        raw_tasks = [{"uuid": "u1", "anchor": "weekday(Mon)"}]
        with patch("scalpel.payload.eprint") as ep:
            _warn_nautical_disabled_if_needed(raw_tasks, enabled=False)
        self.assertTrue(ep.called)

    def test_no_warning_when_enabled(self) -> None:
        raw_tasks = [{"uuid": "u1", "anchor": "weekday(Mon)"}]
        with patch("scalpel.payload.eprint") as ep:
            _warn_nautical_disabled_if_needed(raw_tasks, enabled=True)
        self.assertFalse(ep.called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
