from __future__ import annotations

import datetime as dt
import unittest

from scalpel.util.tz import resolve_tz


class TestTimezoneResolutionContract(unittest.TestCase):
    def test_valid_timezone_identifiers_resolve(self) -> None:
        self.assertEqual(resolve_tz("UTC"), dt.timezone.utc)
        self.assertIsNotNone(resolve_tz("local"))
        self.assertIsNotNone(resolve_tz("+02:00"))

    def test_invalid_timezone_identifiers_raise(self) -> None:
        with self.assertRaises(ValueError):
            resolve_tz("No/Such_Zone")
        with self.assertRaises(ValueError):
            resolve_tz("+25:00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
