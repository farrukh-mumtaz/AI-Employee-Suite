# Cross-agent routing tests: HR Agent and Support Agent, tested against each
# other's domain.
#
# Every other test file exercises one agent at a time. This file is the
# dedicated "cross-test the HR Agent and Support Agent to ensure correct
# routing" check: it feeds Support-domain input through the HR graph/API,
# and HR-domain input through the Support graph/API, and asserts both stay
# within their own lane (routing to "unknown" rather than being
# misclassified into a workflow belonging to the other agent, and without
# either agent's fields leaking into the other's state/response shape).
#
# Deterministic and network-free: each agent's LLM is stubbed with the same
# FakeLLM used by that agent's own test suite (test_hr_agent.py's and
# test_support_agent_graph.py's), so results don't depend on real-model
# behavior -- see test_live_llm_accuracy.py for the live-LLM counterpart of
# this same check.
#
# Run with: python -m pytest test_cross_agent_routing.py -v
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agents.hr_agent import nodes as hr_nodes
from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.agents.support_agent.graph import build_support_graph
from backend.app.main import app

# --- HR (keyword-driven FakeLLM matches hr_agent's own domain vocabulary) ---

_HR_DOMAIN_MESSAGES = [
    "Please onboard John Doe as a Backend Engineer starting next week",
    "New hire, Jane Smith, joining as a Product Manager starting 2026-08-15.",
]
_LEAVE_DOMAIN_MESSAGES = [
    "Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure.",
]

# --- Support-domain messages sent through the HR agent ---

_SUPPORT_DOMAIN_MESSAGES = [
    "I'd like a refund for order #4521, it arrived broken.",
    "I forgot my password and I'm locked out of my account.",
    "Where is my order? It's been two weeks.",
]


class FakeResponse:
    def __init__(self, content):
        self.content = content


class HRFakeLLM:
    """Mirrors test_hr_agent.py's FakeLLM: classifies strictly off HR
    vocabulary (onboard/new hire -> onboarding, leave/vacation/sick ->
    leave_request), so Support-domain input -- which contains none of these
    words -- reliably falls through to "unknown"."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()
        if "intent classifier" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "onboard" in user_message or "new hire" in user_message:
                return FakeResponse("onboarding")
            if "leave" in user_message or "vacation" in user_message or "sick" in user_message:
                return FakeResponse("leave_request")
            return FakeResponse("unknown")

        if "welcoming a new employee" in lowered:
            return FakeResponse("Welcome aboard!")
        if "confirming an approved leave request" in lowered:
            return FakeResponse("Your leave request has been approved.")
        if "responding to a leave request that could not be" in lowered:
            return FakeResponse("Your leave request needs manual review.")

        raise AssertionError(f"HRFakeLLM received an unexpected prompt: {prompt!r}")


class SupportFakeLLM:
    """Mirrors test_support_agent_graph.py's FakeLLM: classifies strictly
    off Support vocabulary (password/locked out -> password_reset,
    refund/return -> refund_request, order/delivery -> order_status), so
    HR-domain input -- which contains none of these words -- reliably falls
    through to "unknown"."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "ticket classification system" in lowered:
            return FakeResponse('{"category": "General Inquiry", "confidence": 0.4}')

        if "intent classifier" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message:
                return FakeResponse("password_reset")
            if "refund" in user_message or "return" in user_message:
                return FakeResponse("refund_request")
            if "order" in user_message or "delivery" in user_message:
                return FakeResponse("order_status")
            return FakeResponse("unknown")

        if "helping a user reset their password" in lowered:
            return FakeResponse("A password reset link has been sent.")
        if "answering an order status question" in lowered:
            return FakeResponse("Your order is being processed.")
        if "processing a refund request" in lowered:
            return FakeResponse("Your refund request has been submitted for manual review.")

        raise AssertionError(f"SupportFakeLLM received an unexpected prompt: {prompt!r}")


class SupportInputThroughHRAgentTests(unittest.TestCase):
    """Support-domain tickets (refunds, password resets, order status) sent
    through the HR graph must never be misrouted into onboarding or
    leave_request -- they carry none of the HR classifier's vocabulary, so
    they must land on "unknown" with HR's clarification message, and none
    of the Support-specific fields (ticket_id, refund_decision, etc.) should
    appear anywhere in HR's state shape."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=HRFakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_support_domain_messages_route_to_unknown(self):
        for text in _SUPPORT_DOMAIN_MESSAGES:
            with self.subTest(user_input=text):
                result = self.graph.invoke(
                    {
                        "messages": [],
                        "user_input": text,
                        "agent_response": None,
                        "agent_name": "hr_agent",
                    }
                )
                self.assertEqual(result["workflow"], "unknown")
                self.assertIn("onboarding", result["agent_response"])
                # No Support-Agent-only fields have ever been introduced into
                # HR's state -- confirms the two agents' state schemas never
                # cross-pollinate.
                self.assertNotIn("ticket_id", result)
                self.assertNotIn("refund_decision", result)
                self.assertNotIn("reset_link_sent", result)

    def test_onboarding_and_leave_are_unaffected_by_the_cross_test(self):
        # Sanity check that the fixture's FakeLLM (and hr_agent's routing
        # generally) still correctly serves its own domain -- a regression
        # here would mean this file was accidentally testing nothing.
        onboarding_result = self.graph.invoke(
            {
                "messages": [],
                "user_input": _HR_DOMAIN_MESSAGES[0],
                "agent_response": None,
                "agent_name": "hr_agent",
            }
        )
        self.assertEqual(onboarding_result["workflow"], "onboarding")

        leave_result = self.graph.invoke(
            {
                "messages": [],
                "user_input": _LEAVE_DOMAIN_MESSAGES[0],
                "agent_response": None,
                "agent_name": "hr_agent",
            }
        )
        self.assertEqual(leave_result["workflow"], "leave_request")


class HRInputThroughSupportAgentTests(unittest.TestCase):
    """HR-domain messages (onboarding, leave requests) sent through the
    Support graph must never be misrouted into password_reset, order_status,
    or refund_request -- they must land on "unknown" with Support's
    clarification message, and none of the HR-specific fields (workflow
    values like onboarding/leave_request, employee_name, leave_decision)
    should leak into Support's result."""

    def setUp(self):
        patcher = patch.object(support_nodes, "get_llm", return_value=SupportFakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_support_graph()

    def test_hr_domain_messages_route_to_unknown(self):
        for text in _HR_DOMAIN_MESSAGES + _LEAVE_DOMAIN_MESSAGES:
            with self.subTest(user_input=text):
                result = self.graph.invoke(
                    {
                        "messages": [],
                        "user_input": text,
                        "agent_response": None,
                        "agent_name": "support_agent",
                    }
                )
                self.assertEqual(result["workflow"], "unknown")
                self.assertIn("password resets", result["agent_response"])
                # A ticket is still created (every Support request gets one,
                # regardless of classification) but no HR-only fields exist.
                self.assertIsNotNone(result.get("ticket_id"))
                self.assertNotIn("employee_name", result)
                self.assertNotIn("leave_decision", result)
                self.assertNotIn("onboarding_checklist", result)

    def test_password_reset_and_refund_are_unaffected_by_the_cross_test(self):
        password_result = self.graph.invoke(
            {
                "messages": [],
                "user_input": "I forgot my password and I'm locked out of my account.",
                "agent_response": None,
                "agent_name": "support_agent",
            }
        )
        self.assertEqual(password_result["workflow"], "password_reset")


class CrossAgentAPIRoutingTests(unittest.TestCase):
    """Same cross-domain checks, but through the real HTTP endpoints
    (POST /hr/message and POST /support/message) -- confirms the isolation
    holds at the API boundary the same way it does at the graph level."""

    def setUp(self):
        hr_patcher = patch.object(hr_nodes, "get_llm", return_value=HRFakeLLM())
        hr_patcher.start()
        self.addCleanup(hr_patcher.stop)

        support_patcher = patch.object(support_nodes, "get_llm", return_value=SupportFakeLLM())
        support_patcher.start()
        self.addCleanup(support_patcher.stop)

        self.client = TestClient(app)

    def test_support_ticket_posted_to_hr_endpoint_is_unknown(self):
        response = self.client.post(
            "/hr/message",
            json={"user_input": "I forgot my password and I'm locked out of my account."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"], "unknown")

    def test_leave_request_posted_to_support_endpoint_is_unknown(self):
        response = self.client.post(
            "/support/message",
            json={
                "user_input": (
                    "Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure."
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workflow"], "unknown")


if __name__ == "__main__":
    unittest.main()
