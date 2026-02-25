import os
import time
import unittest

from scalpel.planner import generate_modify_commands


class TestPlannerCommandsContract(unittest.TestCase):
    def test_generate_modify_commands_uses_local_tz(self) -> None:
        if not hasattr(time, "tzset"):
            self.skipTest("tzset not available")

        old_tz = os.environ.get("TZ")
        os.environ["TZ"] = "UTC"
        time.tzset()
        try:
            events = {
                "abcde-1": (1577871000000, 1577874600000, 60),  # 2020-01-01T10:30 -> 11:30
                "abcde-2": (1577880000000, 1577885400000, 90),  # 2020-01-01T13:00 -> 14:30
            }
            selected = ["abcde-2", "abcde-1"]
            lines = generate_modify_commands(selected, events)
        finally:
            if old_tz is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old_tz
            time.tzset()

        self.assertEqual(
            lines,
            [
                "task abcde-1 modify scheduled:2020-01-01T09:30 due:2020-01-01T10:30 duration:60min",
                "task abcde-2 modify scheduled:2020-01-01T12:00 due:2020-01-01T13:30 duration:90min",
            ],
        )

    def test_generate_modify_commands_uses_full_uuid(self) -> None:
        events = {
            "12345678-aaaa-aaaa-aaaa-aaaaaaaaaaaa": (1577871000000, 1577874600000, 60),
            "12345678-bbbb-bbbb-bbbb-bbbbbbbbbbbb": (1577880000000, 1577883600000, 60),
        }
        selected = [
            "12345678-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "12345678-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        ]
        lines = generate_modify_commands(selected, events)

        first_ident = lines[0].split()[1]
        second_ident = lines[1].split()[1]
        self.assertEqual(first_ident, "12345678-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.assertEqual(second_ident, "12345678-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    def test_generate_modify_commands_shell_quotes_uuid(self) -> None:
        events = {
            "bad;echo PWNED": (1577871000000, 1577874600000, 60),
        }
        selected = ["bad;echo PWNED"]
        lines = generate_modify_commands(selected, events)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("task 'bad;echo PWNED' modify scheduled:"))
        self.assertIn(" due:", lines[0])
        self.assertTrue(lines[0].endswith(" duration:60min"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
