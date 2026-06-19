#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import unittest


class _Result(unittest.TextTestResult):
    skipped_tests: list[tuple[str, str]]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.skipped_tests = []

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802
        super().addSkip(test, reason)
        self.skipped_tests.append((str(test), reason))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run unittest suites with optional skip enforcement.")
    parser.add_argument("--fail-on-skip", action="store_true")
    parser.add_argument("--pattern", default="test_contract_*.py")
    args = parser.parse_args(argv)

    suite = unittest.defaultTestLoader.discover("tests", pattern=args.pattern)

    runner = unittest.TextTestRunner(verbosity=2, resultclass=_Result)
    result = runner.run(suite)
    if args.fail_on_skip and result.skipped_tests:
        for test, reason in result.skipped_tests:
            print(f"unexpected skip: {test}: {reason}", file=sys.stderr)
        return 2
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
