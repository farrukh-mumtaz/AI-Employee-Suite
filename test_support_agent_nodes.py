"""
Unit tests for the Support Agent's ticket_intake_node
(backend/app/agents/support_agent/nodes.py), exercised directly rather
than through the compiled graph. Mirrors the style of test_hr_agent_nodes.py.

No LLM involved -- ticket_intake_node is pure/deterministic -- so nothing
needs to be mocked here.

Run with: python -m unittest test_support_agent_nodes.py -v
"""
import re
import unittest

from backend.app.agents.support_agent import nodes

_TICKET_ID_PATTERN = re.compile(r"^TCK-[0-9A-F]{8}$")


class TicketIntakeNodeTests(unittest.TestCase):
    def test_generates_ticket_id_matching_expected_format(self):
        result = nodes.ticket_intake_node({"user_input": "I need help."})
        self.assertRegex(result["ticket_id"], _TICKET_ID_PATTERN)

    def test_generates_unique_ticket_ids_across_calls(self):
        first = nodes.ticket_intake_node({"user_input": "I need help."})
        second = nodes.ticket_intake_node({"user_input": "I need help."})
        self.assertNotEqual(first["ticket_id"], second["ticket_id"])

    def test_sets_status_open(self):
        result = nodes.ticket_intake_node({"user_input": "I need help."})
        self.assertEqual(result["ticket_status"], "Open")

    def test_returns_only_ticket_intake_keys(self):
        result = nodes.ticket_intake_node({"user_input": "I need help."})
        self.assertEqual(
            set(result.keys()),
            {"ticket_id", "ticket_status", "ticket_priority", "issue_category"},
        )

    def test_does_not_mutate_or_require_user_input_key_elsewhere(self):
        # user_input itself must be left alone -- the node only adds keys.
        state = {"user_input": "My order is late."}
        nodes.ticket_intake_node(state)
        self.assertEqual(state, {"user_input": "My order is late."})

    def test_missing_user_input_does_not_raise(self):
        result = nodes.ticket_intake_node({})
        self.assertEqual(result["ticket_status"], "Open")
        self.assertEqual(result["ticket_priority"], "Medium")
        self.assertEqual(result["issue_category"], "General Support")

    def test_issue_category_defaults_to_general_support(self):
        result = nodes.ticket_intake_node({"user_input": "I need a refund for my order."})
        self.assertEqual(result["issue_category"], "General Support")

    # --- Preserving existing state ---

    def test_does_not_overwrite_an_existing_ticket_id(self):
        state = {"user_input": "I need help.", "ticket_id": "TCK-EXISTING"}
        result = nodes.ticket_intake_node(state)
        self.assertNotIn("ticket_id", result)

    def test_does_not_overwrite_existing_ticket_fields(self):
        state = {
            "user_input": "I need help.",
            "ticket_id": "TCK-EXISTING",
            "ticket_status": "In Progress",
            "ticket_priority": "High",
            "issue_category": "Billing",
        }
        result = nodes.ticket_intake_node(state)
        self.assertEqual(result, {})

    # --- Priority heuristic ---

    def test_high_priority_keyword(self):
        result = nodes.ticket_intake_node(
            {"user_input": "This is urgent, I've been locked out of my account!"}
        )
        self.assertEqual(result["ticket_priority"], "High")

    def test_low_priority_keyword(self):
        result = nodes.ticket_intake_node(
            {"user_input": "Just wondering when my order will arrive, no rush."}
        )
        self.assertEqual(result["ticket_priority"], "Low")

    def test_default_priority_is_medium(self):
        result = nodes.ticket_intake_node({"user_input": "I want to check my order."})
        self.assertEqual(result["ticket_priority"], "Medium")

    def test_high_priority_takes_precedence_over_low(self):
        result = nodes.ticket_intake_node(
            {"user_input": "No rush, but this is actually urgent and unauthorized."}
        )
        self.assertEqual(result["ticket_priority"], "High")

if __name__ == "__main__":
    unittest.main()
