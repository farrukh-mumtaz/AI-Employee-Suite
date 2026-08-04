"""
Support Agent graph tests.

Exercises the compiled Support Agent graph (backend/app/agents/support_agent)
end-to-end for all three supported workflows -- password reset, order
status, refund request -- plus the unknown-intent fallback, with a focus on
verifying that ticket_intake_node runs first and every request ends up with
a ticket regardless of how it's later classified, and that
ticket_classification_node's category/confidence never affect routing.
Mirrors the style of
test_hr_agent.py. The LLM is stubbed via unittest.mock.patch on
`backend.app.agents.support_agent.nodes.get_llm` so the suite runs
deterministically with no network access / GROQ_API_KEY needed.

Run with: python -m unittest test_support_agent_graph.py -v
"""
import re
import unittest
from unittest.mock import patch

from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.agents.support_agent.graph import build_support_graph

_TICKET_ID_PATTERN = re.compile(r"^TCK-[0-9A-F]{8}$")


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Deterministic stand-in for ChatGroq. Chooses a canned response based
    on which prompt template is being invoked, inferred from marker phrases
    that are unique to each prompt in support_agent/prompts.py."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "ticket classification system" in lowered:
            # Same "trailing User message: slice only" reasoning as the
            # intent-classifier branch below -- the category descriptions
            # above it also contain words like "password" and "order".
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message or "log in" in user_message:
                return FakeResponse('{"category": "Password Reset", "confidence": 0.92}')
            if "refund" in user_message or "return" in user_message or "money back" in user_message:
                return FakeResponse('{"category": "Refund", "confidence": 0.9}')
            if "order" in user_message or "delivery" in user_message or "track" in user_message:
                return FakeResponse('{"category": "Order Status", "confidence": 0.88}')
            # Below _TICKET_CATEGORY_CONFIDENCE_THRESHOLD on purpose -- lets
            # the unknown-intent test also exercise the low-confidence ->
            # "Unknown" fallback path.
            return FakeResponse('{"category": "General Inquiry", "confidence": 0.4}')

        if "intent classifier" in lowered:
            # The prompt's instructions describe every category (so they
            # always contain words like "password", "order", "refund") --
            # only the trailing "User message:" section reflects what the
            # user actually said, so classify off of that slice alone.
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message or "log in" in user_message:
                return FakeResponse("password_reset")
            # Checked before order_status: refund mentions ("refund for my
            # order") almost always also contain the generic word "order".
            if "refund" in user_message or "return" in user_message or "money back" in user_message:
                return FakeResponse("refund_request")
            if "order" in user_message or "delivery" in user_message or "track" in user_message:
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
    """Deterministic stand-in for core.rag_node.rag_retrieval_node -- avoids
    hitting the real embedding model / pgvector DB in tests, mirroring how
    FakeLLM stands in for get_llm above."""
    updated = dict(state)
    updated["system_prompt"] = (
        "You are a helpful AI assistant.\n\n"
        "Relevant company information:\n"
        "Refunds are eligible within 30 days of purchase with proof of purchase."
    )
    return updated


def _initial_state(user_input: str) -> dict:
    return {
        "messages": [],
        "user_input": user_input,
        "agent_response": None,
        "agent_name": "support_agent",
    }


class SupportAgentGraphTests(unittest.TestCase):
    def setUp(self):
        # Patch only for the duration of each test; the real support_agent
        # source is never modified.
        patcher = patch.object(support_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)

        rag_patcher = patch.object(
            support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
        )
        rag_patcher.start()
        self.addCleanup(rag_patcher.stop)

        self.graph = build_support_graph()

    def _assert_ticket_created(self, result: dict) -> None:
        self.assertRegex(result["ticket_id"], _TICKET_ID_PATTERN)
        self.assertEqual(result["ticket_status"], "Open")
        self.assertIn(result["ticket_priority"], ("Low", "Medium", "High"))
        # issue_category is a static placeholder set by ticket_intake_node
        # before classification, regardless of which workflow it's later
        # routed to -- see ticket_intake_node's docstring.
        self.assertEqual(result["issue_category"], "General Support")
        # ticket_category/confidence come from ticket_classification_node,
        # which runs before classify_intent and must never affect routing --
        # every workflow branch below still asserts on `workflow` alone.
        self.assertIn(
            result.get("ticket_category"),
            (
                "Refund", "Password Reset", "Billing", "Technical Issue",
                "Account Issue", "Order Status", "General Inquiry", "Unknown",
            ),
        )
        self.assertIsInstance(result.get("ticket_category_confidence"), float)

    def test_password_reset_flow_creates_ticket_and_routes(self):
        result = self.graph.invoke(
            _initial_state("I forgot my password and I'm locked out of my account.")
        )

        self._assert_ticket_created(result)
        self.assertEqual(result["workflow"], "password_reset")
        self.assertTrue(result["reset_link_sent"])
        self.assertIsNotNone(result["agent_response"])

        # Other workflows' fields must never be touched by this branch.
        self.assertIsNone(result.get("order_status"))
        self.assertIsNone(result.get("refund_decision"))

    def test_order_status_flow_creates_ticket_and_routes(self):
        result = self.graph.invoke(
            _initial_state("Where is my order? The tracking page shows nothing.")
        )

        self._assert_ticket_created(result)
        self.assertEqual(result["workflow"], "order_status")
        self.assertIsNotNone(result["order_status"])
        self.assertIsNotNone(result["agent_response"])

        self.assertIsNone(result.get("reset_link_sent"))
        self.assertIsNone(result.get("refund_decision"))

    def test_refund_request_flow_creates_ticket_and_routes(self):
        result = self.graph.invoke(
            _initial_state("I want a refund for my order, it arrived broken.")
        )

        self._assert_ticket_created(result)
        self.assertEqual(result["workflow"], "refund_request")
        self.assertEqual(result["refund_decision"], "pending_manual_review")
        self.assertIn("Refunds are eligible within 30 days", result.get("system_prompt") or "")
        self.assertIsNotNone(result["agent_response"])

        self.assertIsNone(result.get("reset_link_sent"))
        self.assertIsNone(result.get("order_status"))

    def test_unknown_intent_still_creates_a_ticket(self):
        result = self.graph.invoke(_initial_state("What's the weather like today?"))

        self._assert_ticket_created(result)
        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_ticket_ids_are_unique_across_separate_invocations(self):
        first = self.graph.invoke(_initial_state("I forgot my password."))
        second = self.graph.invoke(_initial_state("I forgot my password."))
        self.assertNotEqual(first["ticket_id"], second["ticket_id"])


if __name__ == "__main__":
    unittest.main()
