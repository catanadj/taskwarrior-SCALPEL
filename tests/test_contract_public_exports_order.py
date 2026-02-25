import unittest


class TestPublicExportsOrderContract(unittest.TestCase):
    def test_public_exports_are_sorted_and_consistent(self):
        import scalpel.api as api

        self.assertIsInstance(api._PUBLIC_EXPORTS, tuple)

        # No duplicates
        seen = set()
        for name in api._PUBLIC_EXPORTS:
            self.assertNotIn(name, seen, f"Duplicate in _PUBLIC_EXPORTS: {name}")
            seen.add(name)

        # Alphabetical
        self.assertEqual(list(api._PUBLIC_EXPORTS), sorted(api._PUBLIC_EXPORTS))

        # __all__ respects PUBLIC_EXPORTS order (filtered to defined names)
        expected_all = [n for n in api._PUBLIC_EXPORTS if n in api.__dict__]
        self.assertEqual(api.__all__, expected_all)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
