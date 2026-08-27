from __future__ import annotations

import datetime as dt
import unittest
from unittest.mock import patch

from scalpel.glimpse.app import GlimpseState, _read_search_query, run_interactive, update_state
from scalpel.glimpse.model import GlimpseSnapshot


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
        self.assertEqual(update_state(selected, "w").selected, 1)
        self.assertEqual(update_state(selected, "a").selected, 1)
        self.assertEqual(update_state(selected, "t").day_offset, 0)

    def test_refresh_requests_a_reload_and_closes_details(self) -> None:
        state = GlimpseState(details_visible=True)
        refreshed = update_state(state, "r")
        self.assertTrue(refreshed.refresh_requested)
        self.assertFalse(refreshed.details_visible)

    def test_help_and_quit_are_toggleable(self) -> None:
        state = update_state(GlimpseState(), "?")
        self.assertTrue(state.help_visible)
        self.assertFalse(update_state(state, "?").help_visible)
        self.assertTrue(update_state(state, "q").should_quit)

    def test_selection_never_moves_before_first_item(self) -> None:
        self.assertEqual(update_state(GlimpseState(), "k").selected, 0)

    def test_search_input_restores_noecho_when_reading_fails(self) -> None:
        class BrokenWindow:
            def addstr(self, *_args: object) -> None:
                return None

            def getstr(self, *_args: object) -> bytes:
                raise RuntimeError("input failed")

        with patch("scalpel.glimpse.app.curses.echo") as echo, patch("scalpel.glimpse.app.curses.noecho") as noecho:
            with self.assertRaisesRegex(RuntimeError, "input failed"):
                _read_search_query(BrokenWindow(), 24, 80)  # type: ignore[arg-type]
        echo.assert_called_once()
        noecho.assert_called_once()

    def test_interrupt_is_left_to_curses_wrapper_for_cleanup(self) -> None:
        snapshot = GlimpseSnapshot(dt.date(2026, 8, 27), 1, "UTC", ())
        with patch("scalpel.glimpse.app.curses.wrapper", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run_interactive(snapshot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
