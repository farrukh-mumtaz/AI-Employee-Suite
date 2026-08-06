# API-layer tests for the Support Agent FastAPI endpoint
# (backend/app/api/support.py -- POST /support/message).
#
# Mirrors test_hr_agent_api.py's structure and conventions exactly, since
# the Support Agent's HTTP endpoint was added to bring it to parity with the
# HR Agent's /hr/message (previously the Support Agent could only be invoked
# by building/invoking the graph directly in Python -- see SUPPORT_AGENT.md's
# "Future Improvements"). This file covers request validation, response
# shape, and the endpoint's own error handling -- concerns that only exist at
# the HTTP boundary and aren't exercised by test_support_agent_graph.py /
# test_support_agent_comprehensive.py / test_support_agent_sample_tickets.py.
#
# Uses FastAPI's TestClient against the real `app` from backend/app/main.py,
# with the LLM and shared RAG node stubbed the same way as the rest of the
# suite so it runs deterministically with no network access / GROQ_API_KEY /
# database needed.
#
# Run with: python -m pytest test_support_agent_api.py -v
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.api import support as support_api
from backend.app.main import app


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Same deterministic stand-in used by test_support_agent_graph.py /
    test_support_agent_comprehensive.py, kept in sync so all three files
    agree on what each canned prompt should return."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "ticket classification system" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message:
                return FakeResponse('{"category": "Password Reset", "confidence": 0.9}')
            if "refund" in user_message or "return" in user_message:
                return FakeResponse('{"category": "Refund", "confidence": 0.9}')
            if "order" in user_message or "delivery" in user_message:
                return FakeResponse('{"category": "Order Status", "confidence": 0.9}')
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
            return FakeResponse("A password reset link has been sent to your account email.")

        if "answering an order status question" in lowered:
            return FakeResponse("Your order is currently being processed.")

        if "processing a refund request" in lowered:
            return FakeResponse("Your refund request has been submitted for manual review.")

        raise AssertionError(f"FakeLLM received an unexpected prompt: {prompt!r}")


def _fake_rag_retrieval_node(state: dict) -> dict:
    updated = dict(state)
    updated["system_prompt"] = (
        "You are a helpful AI assistant.\n\n"
        "Relevant company information:\nRefunds are eligible within 30 days of purchase."
    )
    return updated


class SupportMessageEndpointHappyPathTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(support_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)

        rag_patcher = patch.object(
            support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
        )
        rag_patcher.start()
        self.addCleanup(rag_patcher.stop)

        self.client = TestClient(app)

    def test_password_reset_request_returns_200_with_expected_fields(self):
        response = self.client.post(
            "/support/message",
            json={"user_input": "I forgot my password and I'm locked out of my account."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "password_reset")
        self.assertTrue(body["reset_link_sent"])
        self.assertTrue(body["agent_response"])
        self.assertTrue(body["ticket_id"].startswith("TCK-"))
        self.assertEqual(body["ticket_status"], "Open")

    def test_order_status_request_returns_200_with_expected_fields(self):
        response = self.client.post(
            "/support/message",
            json={"user_input": "Where is my order? The tracking page shows nothing."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "order_status")
        self.assertIsNotNone(body["order_status"])
        self.assertTrue(body["agent_response"])

    def test_refund_request_returns_200_with_expected_fields(self):
        response = self.client.post(
            "/support/message",
            json={"user_input": "I want a refund for my order, it arrived broken."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "refund_request")
        self.assertEqual(body["refund_decision"], "pending_manual_review")
        self.assertTrue(body["agent_response"])

    def test_unrecognized_input_falls_back_to_unknown(self):
        response = self.client.post(
            "/support/message", json={"user_input": "What's the weather like today?"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "unknown")
        self.assertTrue(body["agent_response"])
        # Ticket fields must still be populated -- every request gets a
        # ticket regardless of how it's classified.
        self.assertIsNotNone(body["ticket_id"])
        self.assertIsNotNone(body["ticket_category"])


class SupportMessageEndpointInvalidInputTests(unittest.TestCase):
    """No LLM patching needed here -- these requests are rejected by
    Pydantic validation before the graph ever runs."""

    def setUp(self):
        self.client = TestClient(app)

    def test_empty_user_input_returns_422(self):
        response = self.client.post("/support/message", json={"user_input": ""})
        self.assertEqual(response.status_code, 422)

    def test_missing_user_input_field_returns_422(self):
        response = self.client.post("/support/message", json={})
        self.assertEqual(response.status_code, 422)

    def test_wrong_type_for_user_input_returns_422(self):
        response = self.client.post("/support/message", json={"user_input": 12345})
        self.assertEqual(response.status_code, 422)

    def test_non_json_body_returns_422(self):
        response = self.client.post(
            "/support/message",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422)


class SupportMessageEndpointErrorHandlingTests(unittest.TestCase):
    """The endpoint must translate internal failures into a clean 500 rather
    than leaking a raw traceback/500 with no detail."""

    def setUp(self):
        self.client = TestClient(app)

    def test_graph_invocation_failure_returns_500_with_detail(self):
        with patch.object(support_api._support_graph, "invoke", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/support/message", json={"user_input": "I forgot my password."}
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())

    def test_empty_agent_response_returns_500_with_detail(self):
        with patch.object(
            support_api._support_graph,
            "invoke",
            return_value={"workflow": "unknown", "agent_response": None},
        ):
            response = self.client.post(
                "/support/message", json={"user_input": "I forgot my password."}
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
