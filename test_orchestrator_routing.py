# API-layer tests for the Orchestrator FastAPI endpoint
# (backend/app/api/orchestrator.py -- POST /agent/message).
#
# Mirrors test_hr_agent_api.py's and test_support_agent_api.py's structure
# and conventions exactly: a HappyPathTests class per workflow, an
# InvalidInputTests class covering Pydantic-level rejection, and an
# ErrorHandlingTests class covering the endpoint's own failure handling.
# OrchestratorGraphRoutingTests below is the orchestrator's own analogue of
# test_hr_agent_graph.py / test_support_agent_graph.py -- it exercises
# build_orchestrator_graph() directly (no HTTP layer), confirming the routing
# decision itself, which the HTTP-layer tests don't re-derive.
#
# Uses FastAPI's TestClient against the real `app` from backend/app/main.py.
# The orchestrator's own routing LLM call is stubbed via a FakeLLM patched
# onto backend.app.core.orchestrator.get_llm, and each sub-graph's LLM calls
# are stubbed the same way test_cross_agent_routing.py does it (patched onto
# hr_nodes.get_llm / support_nodes.get_llm), so results don't depend on
# real-model behavior / network access / GROQ_API_KEY.
#
# Run with: python -m pytest test_orchestrator_routing.py -v
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agents.hr_agent import nodes as hr_nodes
from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.api import orchestrator as orchestrator_api
from backend.app.core import orchestrator
from backend.app.core.orchestrator import build_orchestrator_graph
from backend.app.main import app


class FakeResponse:
    def __init__(self, content):
        self.content = content


class RouteFakeLLM:
    """Classifies strictly off HR vs Support vocabulary, mirroring the
    orchestrator's own ROUTE_AGENT_PROMPT wording. Anything without HR
    vocabulary defaults to "support", matching
    classify_target_agent_node's own documented fallback."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()
        if "routing classifier" not in lowered:
            raise AssertionError(f"RouteFakeLLM received an unexpected prompt: {prompt!r}")

        user_message = lowered.rsplit("user message:", 1)[-1]
        if "onboard" in user_message or "new hire" in user_message or "leave" in user_message:
            return FakeResponse("hr")
        return FakeResponse("support")


class HRFakeLLM:
    """Same deterministic stand-in used by test_hr_agent_api.py and
    test_cross_agent_routing.py, kept in sync so every file agrees on what
    each canned prompt should return."""

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
    """Same deterministic stand-in used by test_support_agent_api.py and
    test_cross_agent_routing.py, kept in sync so every file agrees on what
    each canned prompt should return."""

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


class OrchestratorGraphRoutingTests(unittest.TestCase):
    """Exercises build_orchestrator_graph() directly -- the orchestrator's
    analogue of test_hr_agent_graph.py / test_support_agent_graph.py."""

    def setUp(self):
        route_patcher = patch.object(orchestrator, "get_llm", return_value=RouteFakeLLM())
        route_patcher.start()
        self.addCleanup(route_patcher.stop)

        hr_patcher = patch.object(hr_nodes, "get_llm", return_value=HRFakeLLM())
        hr_patcher.start()
        self.addCleanup(hr_patcher.stop)

        support_patcher = patch.object(support_nodes, "get_llm", return_value=SupportFakeLLM())
        support_patcher.start()
        self.addCleanup(support_patcher.stop)

        self.graph = build_orchestrator_graph()

    def test_onboarding_message_routes_to_hr_agent(self):
        result = self.graph.invoke(
            {
                "messages": [],
                "user_input": "Please onboard John Doe as a Backend Engineer starting next week",
                "agent_response": None,
                "agent_name": "orchestrator",
            }
        )
        self.assertEqual(result["target_agent"], "hr")
        self.assertIsNone(result.get("support_result"))
        self.assertEqual(result["hr_result"]["workflow"], "onboarding")

    def test_password_reset_message_routes_to_support_agent(self):
        result = self.graph.invoke(
            {
                "messages": [],
                "user_input": "I forgot my password and I'm locked out of my account.",
                "agent_response": None,
                "agent_name": "orchestrator",
            }
        )
        self.assertEqual(result["target_agent"], "support")
        self.assertIsNone(result.get("hr_result"))
        self.assertEqual(result["support_result"]["workflow"], "password_reset")


class AgentMessageEndpointHappyPathTests(unittest.TestCase):
    def setUp(self):
        route_patcher = patch.object(orchestrator, "get_llm", return_value=RouteFakeLLM())
        route_patcher.start()
        self.addCleanup(route_patcher.stop)

        hr_patcher = patch.object(hr_nodes, "get_llm", return_value=HRFakeLLM())
        hr_patcher.start()
        self.addCleanup(hr_patcher.stop)

        support_patcher = patch.object(support_nodes, "get_llm", return_value=SupportFakeLLM())
        support_patcher.start()
        self.addCleanup(support_patcher.stop)

        self.client = TestClient(app)

    def test_onboarding_request_dispatches_to_hr_agent(self):
        response = self.client.post(
            "/agent/message",
            json={
                "user_input": (
                    "New hire, Jane Smith, joining as a Product Manager starting 2026-08-15."
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent"], "hr")
        self.assertIsNone(body["support"])
        self.assertEqual(body["hr"]["workflow"], "onboarding")
        self.assertEqual(body["hr"]["employee_name"], "Jane Smith")
        self.assertTrue(body["hr"]["agent_response"])

    def test_leave_request_dispatches_to_hr_agent(self):
        response = self.client.post(
            "/agent/message",
            json={"user_input": "Requesting sick leave from Aug 1 to Aug 3."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent"], "hr")
        self.assertIsNone(body["support"])
        self.assertEqual(body["hr"]["workflow"], "leave_request")
        self.assertTrue(body["hr"]["agent_response"])

    def test_password_reset_request_dispatches_to_support_agent(self):
        response = self.client.post(
            "/agent/message",
            json={"user_input": "I forgot my password and I'm locked out of my account."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent"], "support")
        self.assertIsNone(body["hr"])
        self.assertEqual(body["support"]["workflow"], "password_reset")
        self.assertTrue(body["support"]["reset_link_sent"])
        self.assertTrue(body["support"]["agent_response"])

    def test_refund_request_dispatches_to_support_agent(self):
        response = self.client.post(
            "/agent/message",
            json={"user_input": "I'd like a refund for order #4521, it arrived broken."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent"], "support")
        self.assertIsNone(body["hr"])
        self.assertEqual(body["support"]["workflow"], "refund_request")
        self.assertTrue(body["support"]["agent_response"])

    def test_unrecognized_input_defaults_to_support_with_unknown_workflow(self):
        # No HR or Support vocabulary: the orchestrator's own classifier has
        # no "unknown" target (see classify_target_agent_node), so it falls
        # back to "support" -- which still creates a ticket and lands on
        # workflow "unknown" once Support's own classifier also can't match
        # it, rather than the message being dropped.
        response = self.client.post(
            "/agent/message", json={"user_input": "What's the weather like today?"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent"], "support")
        self.assertIsNone(body["hr"])
        self.assertEqual(body["support"]["workflow"], "unknown")
        self.assertIsNotNone(body["support"]["ticket_id"])
        self.assertTrue(body["support"]["agent_response"])


class AgentMessageEndpointInvalidInputTests(unittest.TestCase):
    """No LLM patching needed here -- these requests are rejected by Pydantic
    validation before the orchestrator graph ever runs."""

    def setUp(self):
        self.client = TestClient(app)

    def test_empty_user_input_returns_422(self):
        response = self.client.post("/agent/message", json={"user_input": ""})
        self.assertEqual(response.status_code, 422)

    def test_missing_user_input_field_returns_422(self):
        response = self.client.post("/agent/message", json={})
        self.assertEqual(response.status_code, 422)

    def test_wrong_type_for_user_input_returns_422(self):
        response = self.client.post("/agent/message", json={"user_input": 12345})
        self.assertEqual(response.status_code, 422)

    def test_non_json_body_returns_422(self):
        response = self.client.post(
            "/agent/message",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422)


class AgentMessageEndpointErrorHandlingTests(unittest.TestCase):
    """The endpoint must translate internal failures into a clean 500 rather
    than leaking a raw traceback -- mirrors HR/Support's own error-handling
    coverage for their endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_graph_invocation_failure_returns_500_with_detail(self):
        with patch.object(
            orchestrator_api._orchestrator_graph, "invoke", side_effect=RuntimeError("boom")
        ):
            response = self.client.post("/agent/message", json={"user_input": "Onboard our new hire."})
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())

    def test_empty_agent_response_returns_500_with_detail(self):
        with patch.object(
            orchestrator_api._orchestrator_graph,
            "invoke",
            return_value={"target_agent": "hr", "hr_result": {"workflow": "unknown", "agent_response": None}},
        ):
            response = self.client.post("/agent/message", json={"user_input": "Onboard our new hire."})
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())

    def test_hr_result_missing_workflow_key_degrades_to_unknown_instead_of_500(self):
        # hr_state.get("workflow", "unknown") must apply even when the
        # sub-graph's result omits the key entirely, matching /hr/message's
        # own defensive default -- a blind **hr_state spread would instead
        # raise an unhandled pydantic.ValidationError here.
        with patch.object(
            orchestrator_api._orchestrator_graph,
            "invoke",
            return_value={
                "target_agent": "hr",
                "hr_result": {"agent_response": "Welcome aboard!"},
            },
        ):
            response = self.client.post("/agent/message", json={"user_input": "Onboard our new hire."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["hr"]["workflow"], "unknown")


if __name__ == "__main__":
    unittest.main()
