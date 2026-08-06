"""
Unit tests for backend/app/agents/hr_agent/extraction.py.

Pure-function tests -- no LLM, no graph, no mocking needed. These pin down
the regex/keyword heuristics so future edits to extraction.py don't
silently change what gets pulled out of user text.

Run with: python -m unittest test_hr_agent_extraction.py -v
"""
import unittest

from backend.app.agents.hr_agent import extraction


class ExtractNameTests(unittest.TestCase):
    def test_name_is_pattern(self):
        self.assertEqual(
            extraction.extract_name("The new employee's name is Jane Smith."),
            "Jane Smith",
        )

    def test_new_hire_pattern(self):
        self.assertEqual(
            extraction.extract_name("Please onboard our new hire, Jane Smith, starting Monday."),
            "Jane Smith",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(extraction.extract_name("We have a new hire starting next week."))


class ExtractRoleTests(unittest.TestCase):
    def test_as_a_pattern_stops_before_temporal_clause(self):
        self.assertEqual(
            extraction.extract_role("Jane starts as a Product Manager next Monday."),
            "Product Manager",
        )

    def test_role_of_pattern(self):
        self.assertEqual(
            extraction.extract_role("Role of Backend Engineer, starting Aug 1."),
            "Backend Engineer",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(extraction.extract_role("We have a new hire starting next week."))


class ExtractDatesTests(unittest.TestCase):
    def test_absolute_dates_in_order(self):
        dates = extraction.extract_dates("Leave from Aug 1 to Aug 3.", max_dates=2)
        self.assertEqual(dates, ["Aug 1", "Aug 3"])

    def test_iso_date(self):
        self.assertEqual(extraction.extract_dates("Starting 2026-08-01."), ["2026-08-01"])

    def test_falls_back_to_relative_phrase(self):
        self.assertEqual(
            extraction.extract_dates("Starting onboarding next week."),
            ["next week"],
        )

    def test_no_match_returns_empty_list(self):
        self.assertEqual(extraction.extract_dates("No dates mentioned here."), [])

    def test_respects_max_dates(self):
        dates = extraction.extract_dates("Aug 1, Aug 2, Aug 3", max_dates=2)
        self.assertEqual(len(dates), 2)


class ExtractLeaveTypeTests(unittest.TestCase):
    def test_sick_leave(self):
        self.assertEqual(
            extraction.extract_leave_type("I'm feeling unwell and need sick leave."),
            "sick leave",
        )

    def test_vacation(self):
        self.assertEqual(
            extraction.extract_leave_type("Requesting vacation for next week."),
            "vacation",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(extraction.extract_leave_type("I need some time off."))


class ExtractLeaveReasonTests(unittest.TestCase):
    """Covers extraction.extract_leave_reason, added to support the leave
    workflow's reason field (backend/app/agents/hr_agent/state.py
    leave_reason). No prior test file covered this function."""

    def test_because_of_pattern(self):
        self.assertEqual(
            extraction.extract_leave_reason(
                "Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure."
            ),
            "a medical procedure",
        )

    def test_because_pattern_stops_before_temporal_clause(self):
        self.assertEqual(
            extraction.extract_leave_reason(
                "I need leave because I have a family emergency starting Monday."
            ),
            "I have a family emergency",
        )

    def test_due_to_pattern(self):
        self.assertEqual(
            extraction.extract_leave_reason("Requesting personal leave due to a family emergency."),
            "a family emergency",
        )

    def test_reason_colon_pattern(self):
        self.assertEqual(
            extraction.extract_leave_reason(
                "Requesting unpaid leave, reason: relocating to a new apartment."
            ),
            "relocating to a new apartment",
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(extraction.extract_leave_reason("I need some time off."))

    def test_bare_for_clause_is_not_treated_as_a_reason(self):
        # Deliberate design choice: a bare "for ..." marker is not matched
        # (unlike "because of"/"due to"/"reason:") since it collides with
        # duration phrasing like "leave for 3 days" -- see extraction.py's
        # _LEAVE_REASON_PATTERNS comment.
        self.assertIsNone(
            extraction.extract_leave_reason(
                "I need to take vacation from 2026-09-01 to 2026-09-05 for my sister's wedding."
            )
        )


if __name__ == "__main__":
    unittest.main()
