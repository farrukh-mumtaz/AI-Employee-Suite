"""
Unit tests for individual HR Agent node functions
(backend/app/agents/hr_agent/nodes.py), exercised directly rather than
through the compiled graph. This complements test_hr_agent.py (which tests
the graph end-to-end) by pinning down each node's behavior in isolation --
in particular the partial-state-update contract and LLM-failure fallbacks.

get_llm is stubbed via unittest.mock.patch so these run deterministically
with no network access / GROQ_API_KEY needed.

Run with: python -m unittest test_hr_agent_nodes.py -v
"""
import unittest
from unittest.mock import patch

from backend.app.agents.hr_agent import nodes


class FakeResponse:
    def __init__(self, content):
        self.content = content


class RaisingLLM:
    """Stands in for an LLM client whose call fails (network error, bad
    API key, provider outage, etc.)."""

    def invoke(self, prompt):
        raise RuntimeError("simulated LLM/network failure")


class ClassifyIntentNodeTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_returns_only_workflow_key(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = FakeResponse("onboarding")
        result = nodes.classify_intent_node({"user_input": "Onboard our new hire."})
        self.assertEqual(result, {"workflow": "onboarding"})

    @patch.object(nodes, "get_llm")
    def test_unrecognized_llm_output_maps_to_unknown(self, mock_get_llm):
        mock_get_llm.return_value.invoke.return_value = FakeResponse("something else")
        result = nodes.classify_intent_node({"user_input": "asdf"})
        self.assertEqual(result, {"workflow": "unknown"})

    @patch.object(nodes, "get_llm")
    def test_llm_failure_falls_back_to_unknown(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.classify_intent_node({"user_input": "Onboard our new hire."})
        self.assertEqual(result, {"workflow": "unknown"})

    @patch.object(nodes, "get_llm")
    def test_empty_input_skips_llm_call_entirely(self, mock_get_llm):
        result = nodes.classify_intent_node({"user_input": "   "})
        self.assertEqual(result, {"workflow": "unknown"})
        mock_get_llm.assert_not_called()


class ExtractEmployeeDetailsNodeTests(unittest.TestCase):
    def test_extracts_from_user_input_when_absent(self):
        state = {"user_input": "New hire, Jane Smith, starts as a Product Manager next Monday."}
        result = nodes.extract_employee_details_node(state)
        self.assertEqual(result["employee_name"], "Jane Smith")
        self.assertEqual(result["employee_role"], "Product Manager")

    def test_falls_back_to_unknown_when_nothing_found(self):
        state = {"user_input": "We have a new hire starting next week."}
        result = nodes.extract_employee_details_node(state)
        self.assertEqual(result["employee_name"], "Unknown")
        self.assertEqual(result["employee_role"], "Unknown")
        self.assertEqual(result["start_date"], "next week")

    def test_does_not_overwrite_preexisting_values(self):
        state = {
            "user_input": "New hire, Jane Smith, starts as a Product Manager.",
            "employee_name": "Provided Name",
        }
        result = nodes.extract_employee_details_node(state)
        self.assertNotIn("employee_name", result)


class ExtractLeaveDetailsNodeTests(unittest.TestCase):
    def test_two_dates_map_to_start_and_end(self):
        state = {"user_input": "Requesting sick leave from Aug 1 to Aug 3."}
        result = nodes.extract_leave_details_node(state)
        self.assertEqual(result["leave_type"], "sick leave")
        self.assertEqual(result["leave_start_date"], "Aug 1")
        self.assertEqual(result["leave_end_date"], "Aug 3")

    def test_single_date_used_for_both_start_and_end(self):
        state = {"user_input": "I need sick leave on 2026-08-01."}
        result = nodes.extract_leave_details_node(state)
        self.assertEqual(result["leave_start_date"], "2026-08-01")
        self.assertEqual(result["leave_end_date"], "2026-08-01")

    def test_falls_back_to_unspecified(self):
        state = {"user_input": "I need some time off."}
        result = nodes.extract_leave_details_node(state)
        self.assertEqual(result["leave_type"], "Unspecified")
        self.assertEqual(result["leave_start_date"], "Unspecified")
        self.assertEqual(result["leave_end_date"], "Unspecified")


class GenerateWelcomeMessageNodeTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_llm_failure_uses_readable_fallback(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        state = {"employee_name": "Jane Smith", "employee_role": "Product Manager"}
        result = nodes.generate_welcome_message_node(state)
        self.assertIn("Jane Smith", result["agent_response"])
        self.assertIn("Product Manager", result["agent_response"])


class GenerateOnboardingChecklistNodeTests(unittest.TestCase):
    def test_returns_independent_copy_of_template(self):
        from backend.app.agents.hr_agent import prompts

        result = nodes.generate_onboarding_checklist_node({})
        result["onboarding_checklist"].append("mutated")
        self.assertNotIn("mutated", prompts.ONBOARDING_CHECKLIST_TEMPLATE)


class EvaluateLeaveRequestNodeTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_always_pending_review_even_when_llm_fails(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        state = {"user_input": "Requesting leave.", "leave_policy_context": []}
        result = nodes.evaluate_leave_request_node(state)
        self.assertEqual(result["leave_decision"], "pending_manual_review")
        self.assertIsInstance(result["agent_response"], str)
        self.assertTrue(result["agent_response"])


class UnknownIntentNodeTests(unittest.TestCase):
    def test_returns_clarification_message(self):
        result = nodes.unknown_intent_node({})
        self.assertIn("onboarding", result["agent_response"].lower())
        self.assertIn("leave", result["agent_response"].lower())


if __name__ == "__main__":
    unittest.main()
