from __future__ import annotations

import unittest


class TestPublicApiLockContract(unittest.TestCase):
    def test_api_module_exports_are_present(self) -> None:
        import scalpel.api as api

        self.assertTrue(hasattr(api, "__all__"))
        self.assertIsInstance(api.__all__, (list, tuple))
        self.assertGreaterEqual(len(api.__all__), 3)

        for name in api.__all__:
            self.assertIsInstance(name, str)
            self.assertTrue(hasattr(api, name), f"scalpel.api missing public name: {name}")
            obj = getattr(api, name)
            self.assertIsNotNone(obj, f"scalpel.api {name} is None")

    def test_package_reexports_match_api_all(self) -> None:
        import scalpel
        import scalpel.api as api

        for name in api.__all__:
            self.assertTrue(hasattr(scalpel, name), f"scalpel package does not re-export: {name}")
            self.assertIs(getattr(scalpel, name), getattr(api, name), f"scalpel.{name} must be same object as scalpel.api.{name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
