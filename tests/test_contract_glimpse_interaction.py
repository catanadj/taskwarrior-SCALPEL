from __future__ import annotations

import unittest

from scalpel.glimpse.app import GlimpseState, update_state


class GlimpseInteractionContractTests(unittest.TestCase):
    def test_view_navigation_and_day_navigation_are_pure(self) -> None:
        initial = GlimpseState()
        day = update_state(initial, "d")
        moved = update_state(day, "l")
        selected = update_state(moved, "j")
        self.assertEqual(initial, GlimpseState())
        self.assertEqual(day.view, "day")
        self.assertEqual(moved.day_offset, 1)
        self.assertEqual(selected.selected, 1)
        self.assertEqual(update_state(selected, "t").day_offset, 0)

    def test_help_and_quit_are_toggleable(self) -> None:
        state = update_state(GlimpseState(), "?")
        self.assertTrue(state.help_visible)
        self.assertFalse(update_state(state, "?").help_visible)
        self.assertTrue(update_state(state, "q").should_quit)

    def test_selection_never_moves_before_first_item(self) -> None:
        self.assertEqual(update_state(GlimpseState(), "k").selected, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
