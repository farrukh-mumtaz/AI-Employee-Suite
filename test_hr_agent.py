"""
HR Agent tests.

Exercises the real HR Agent graph (backend/app/agents/hr_agent) end-to-end
for both supported workflows -- Employee Onboarding and Leave Requests --
plus the unknown-intent fallback. The LLM is stubbed out via
unittest.mock.patch on `backend.app.agents.hr_agent.nodes.get_llm` so the
suite runs deterministically with no network access / GROQ_API_KEY needed;
everything else (graph construction, conditional routing, node execution,
state mutation) runs unmodified.

Run with: python -m unittest test_hr_agent.py -v
"""
import unittest
from unittest.mock import patch

from backend.app.agents.hr_agent import nodes as hr_nodes
from backend.app.agents.hr_agent.graph import build_hr_graph


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Deterministic stand-in for ChatGroq. Chooses a canned response based
    on which prompt template is being invoked, inferred from marker phrases
    that are unique to each prompt in hr_agent/prompts.py."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "intent classifier" in lowered:
            # The prompt's instructions describe every category (so they
            # always contain the word "onboarding", "leave", etc.) -- only
            # the trailing "User message:" section reflects what the user
            # actually said, so classify off of that slice alone.
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "onboard" in user_message or "new hire" in user_message:
                return FakeResponse("onboarding")
            if "leave" in user_message or "vacation" in user_message or "sick" in user_message:
                return FakeResponse("leave_request")
            return FakeResponse("unknown")

        if "welcoming a new employee" in lowered:
            return FakeResponse("Welcome aboard! We're excited to have you join us.")

        if "confirming an approved leave request" in lowered:
            return FakeResponse("Your leave request has been approved. Enjoy your time off!")

        if "responding to a leave request that could not be" in lowered:
            return FakeResponse(
                "We couldn't automatically process your leave request; it has "
                "been forwarded to HR for manual review."
            )

        raise AssertionError(f"FakeLLM received an unexpected prompt: {prompt!r}")


def _initial_state(user_input: str) -> dict:
    return {
        "messages": [],
        "user_input": user_input,
        "agent_response": None,
        "agent_name": "hr_agent",
    }


class HRAgentGraphTests(unittest.TestCase):
    def setUp(self):
        # Patch only for the duration of each test; the real hr_agent
        # source is never modified.
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_leave_request_with_full_details_is_approved(self):
        result = self.graph.invoke(
            _initial_state(
                "I need to request sick leave from Aug 1 to Aug 3, I'm unwell."
            )
        )

        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "sick leave")
        self.assertEqual(result["leave_start_date"], "Aug 1")
        self.assertEqual(result["leave_end_date"], "Aug 3")
        self.assertEqual(result["leave_decision"], "approved")
        self.assertIsInstance(result["leave_policy_context"], list)
        self.assertGreater(len(result["leave_policy_context"]), 0)
        self.assertEqual(
            result["agent_response"],
            "Your leave request has been approved. Enjoy your time off!",
        )

        # Onboarding-only fields must never be touched by this branch.
        self.assertIsNone(result.get("employee_name"))
        self.assertIsNone(result.get("onboarding_checklist"))

    def test_leave_request_with_missing_details_is_rejected_for_manual_review(self):
        result = self.graph.invoke(
            _initial_state("I'd like to request leave but haven't decided on dates yet.")
        )

        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "Unspecified")
        self.assertEqual(result["leave_decision"], "rejected")
        self.assertEqual(
            result["agent_response"],
            "We couldn't automatically process your leave request; it has "
            "been forwarded to HR for manual review.",
        )

        # Onboarding-only fields must never be touched by this branch.
        self.assertIsNone(result.get("employee_name"))
        self.assertIsNone(result.get("onboarding_checklist"))

    def test_onboarding_flow_routes_and_updates_state(self):
        result = self.graph.invoke(
            _initial_state("We have a new hire starting onboarding next week.")
        )

        self.assertEqual(result["workflow"], "onboarding")
        self.assertIsInstance(result["onboarding_checklist"], list)
        self.assertGreater(len(result["onboarding_checklist"]), 0)
        self.assertIsNotNone(result["agent_response"])

        # Leave-request-only fields must never be touched by this branch.
        self.assertIsNone(result.get("leave_decision"))
        self.assertIsNone(result.get("leave_policy_context"))

    def test_unknown_intent_falls_back_gracefully(self):
        result = self.graph.invoke(
            _initial_state("What's the weather like today?")
        )

        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])
        self.assertIsNone(result.get("leave_decision"))
        self.assertIsNone(result.get("onboarding_checklist"))


if __name__ == "__main__":
    unittest.main()
