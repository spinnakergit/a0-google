"""Regression tests for attendees / recurrence parsing in calendar tools.

These tests pin the contract that ``attendees`` and ``recurrence`` MUST
accept both:

  * a string (legacy / backward-compat shape)
  * a list of strings (the shape declared by the tool prompts)

without raising ``AttributeError`` (the bug fixed in
spinnakergit/a0-google#2 and its follow-up).

The tests are intentionally stdlib-only so they can run anywhere without
the Agent Zero runtime:

  * Reference implementations encode the desired behavior parametrically.
  * Structural "canary" tests read the production source files and assert
    they retain the ``isinstance(..., str)`` guard, so any future refactor
    that drops the guard will trip a clearly-named test.

Run with either::

    python tests/test_calendar_parsing.py
    pytest tests/test_calendar_parsing.py
"""

from __future__ import annotations

import pathlib
import re
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CALENDAR_CREATE = REPO_ROOT / "tools" / "calendar_create.py"
CALENDAR_UPDATE = REPO_ROOT / "tools" / "calendar_update.py"


def parse_attendees(value):
    """Reference implementation. Mirrors the production contract.

    Returns ``None`` for falsy input. Otherwise returns a stripped,
    non-empty list of strings, accepting either a comma-separated string
    or an iterable of strings.
    """
    if not value:
        return None
    if isinstance(value, str):
        return [a.strip() for a in value.split(",") if a.strip()]
    return [a.strip() for a in value if a.strip()]


def parse_recurrence(value):
    """Reference implementation for recurrence parsing in calendar_create.

    Splits a string on newlines (NOT semicolons, which are used within
    RRULE syntax) or iterates a list. Then ensures every entry starts
    with the ``RRULE:`` prefix.
    """
    if not value:
        return None
    if isinstance(value, str):
        items = [r.strip() for r in value.split("\n") if r.strip()]
    else:
        items = [r.strip() for r in value if r.strip()]
    return [r if r.startswith("RRULE:") else f"RRULE:{r}" for r in items]


class AttendeesParsingTests(unittest.TestCase):
    def test_falsy_returns_none(self):
        for v in ("", None, [], 0, False):
            with self.subTest(value=v):
                self.assertIsNone(parse_attendees(v))

    def test_single_string(self):
        self.assertEqual(parse_attendees("alice@x.com"), ["alice@x.com"])

    def test_csv_string(self):
        self.assertEqual(
            parse_attendees("alice@x.com,bob@x.com"),
            ["alice@x.com", "bob@x.com"],
        )

    def test_csv_string_with_whitespace_and_blanks(self):
        self.assertEqual(
            parse_attendees(" alice@x.com , bob@x.com ,, carol@x.com "),
            ["alice@x.com", "bob@x.com", "carol@x.com"],
        )

    def test_list_input_does_not_raise(self):
        # The original bug: AttributeError: 'list' object has no attribute 'split'
        try:
            parse_attendees(["alice@x.com", "bob@x.com"])
        except AttributeError as e:  # pragma: no cover - regression guard
            self.fail(f"parse_attendees raised AttributeError on list input: {e}")

    def test_list_input(self):
        self.assertEqual(
            parse_attendees(["alice@x.com", "bob@x.com"]),
            ["alice@x.com", "bob@x.com"],
        )

    def test_list_input_with_whitespace_and_blanks(self):
        self.assertEqual(
            parse_attendees([" alice@x.com ", "bob@x.com", "", "  ", "carol@x.com "]),
            ["alice@x.com", "bob@x.com", "carol@x.com"],
        )

    def test_string_and_list_produce_equivalent_output(self):
        as_string = "alice@x.com,bob@x.com,carol@x.com"
        as_list = ["alice@x.com", "bob@x.com", "carol@x.com"]
        self.assertEqual(parse_attendees(as_string), parse_attendees(as_list))


class RecurrenceParsingTests(unittest.TestCase):
    def test_falsy_returns_none(self):
        for v in ("", None, [], 0, False):
            with self.subTest(value=v):
                self.assertIsNone(parse_recurrence(v))

    def test_string_with_rrule_prefix(self):
        self.assertEqual(
            parse_recurrence("RRULE:FREQ=WEEKLY;BYDAY=MO"),
            ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        )

    def test_string_without_rrule_prefix_gets_one(self):
        self.assertEqual(
            parse_recurrence("FREQ=WEEKLY;BYDAY=MO"),
            ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
        )

    def test_string_with_multiple_newline_separated_rules(self):
        self.assertEqual(
            parse_recurrence("RRULE:FREQ=WEEKLY\nRRULE:FREQ=MONTHLY"),
            ["RRULE:FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"],
        )

    def test_does_not_split_on_semicolons(self):
        # Semicolons are part of RRULE syntax (BYDAY=MO,WE,FR;BYHOUR=9).
        # Splitting on ';' would shred a single rule into garbage.
        out = parse_recurrence("RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9")
        self.assertEqual(out, ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9"])

    def test_list_input_does_not_raise(self):
        try:
            parse_recurrence(["RRULE:FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"])
        except AttributeError as e:  # pragma: no cover - regression guard
            self.fail(f"parse_recurrence raised AttributeError on list input: {e}")

    def test_list_input(self):
        self.assertEqual(
            parse_recurrence(["RRULE:FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"]),
            ["RRULE:FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"],
        )

    def test_list_input_adds_missing_rrule_prefix(self):
        self.assertEqual(
            parse_recurrence(["FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"]),
            ["RRULE:FREQ=WEEKLY", "RRULE:FREQ=MONTHLY"],
        )


class ProductionSourceCanaryTests(unittest.TestCase):
    """Structural canaries: any future refactor that drops the type guard
    in the production tools will fail one of these tests with a clear name.
    """

    def _read(self, path: pathlib.Path) -> str:
        self.assertTrue(path.exists(), f"missing source file: {path}")
        return path.read_text(encoding="utf-8")

    def test_calendar_create_has_attendees_isinstance_guard(self):
        src = self._read(CALENDAR_CREATE)
        self.assertRegex(
            src,
            r"isinstance\(\s*attendees\s*,\s*str\s*\)",
            "calendar_create.py must guard attendees with isinstance(..., str) "
            "before calling .split(',') — regression of spinnakergit/a0-google#2",
        )

    def test_calendar_update_has_attendees_isinstance_guard(self):
        src = self._read(CALENDAR_UPDATE)
        self.assertRegex(
            src,
            r"isinstance\(\s*attendees\s*,\s*str\s*\)",
            "calendar_update.py must guard attendees with isinstance(..., str) "
            "before calling .split(',') — regression of spinnakergit/a0-google#2",
        )

    def test_calendar_create_has_recurrence_isinstance_guard(self):
        src = self._read(CALENDAR_CREATE)
        self.assertRegex(
            src,
            r"isinstance\(\s*recurrence\s*,\s*str\s*\)",
            "calendar_create.py must guard recurrence with isinstance(..., str) "
            "before calling .split('\\n')",
        )

    def test_no_unguarded_split_on_attendees(self):
        for path in (CALENDAR_CREATE, CALENDAR_UPDATE):
            src = self._read(path)
            # Strip the legitimate guarded usage so a regression actually trips.
            stripped = re.sub(
                r"isinstance\(\s*attendees\s*,\s*str\s*\)\s*:\s*\n\s*"
                r"attendee_list\s*=\s*\[[^\n]*attendees\.split\([^\n]*\][^\n]*",
                "",
                src,
            )
            self.assertNotIn(
                "attendees.split(",
                stripped,
                f"{path.name} contains an unguarded attendees.split(...) call",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
