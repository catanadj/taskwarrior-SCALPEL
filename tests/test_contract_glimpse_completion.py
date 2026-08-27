from __future__ import annotations

import unittest
from pathlib import Path

from scalpel.glimpse.cli import build_parser


class GlimpseCompletionContractTests(unittest.TestCase):
    def test_bash_completion_mentions_every_long_cli_option(self) -> None:
        completion = Path("contrib/completions/scalpel-glimpse.bash").read_text(encoding="utf-8")
        actions = build_parser()._actions
        options = {option for action in actions for option in action.option_strings if option.startswith("--")}
        missing = sorted(option for option in options if option not in completion)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
