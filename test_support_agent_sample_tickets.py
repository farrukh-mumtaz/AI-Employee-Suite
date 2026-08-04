"""
Support Agent realistic sample-ticket suite.

Exercises the compiled Support Agent graph end-to-end against >=20 realistic
support tickets spanning all 7 ticket_classification_node categories (Refund,
Password Reset, Billing, Technical Issue, Account Issue, Order Status,
General Inquiry) plus a handful of unrelated/low-confidence "Unknown
Requests", asserting the full expected shape -- ticket category, workflow
routing, and final response -- for each one in a single table-driven test.

Only 3 of the 7 ticket categories (Refund, Password Reset, Order Status)
have a dedicated workflow branch today; the rest correctly route to
`workflow="unknown"` and get the standard clarification response --
ticket_category and workflow are deliberately independent (see
ticket_classification_node's docstring in nodes.py).

Complements, does not replace, the scenario-focused tests in
test_support_agent_graph.py and test_support_agent_comprehensive.py.

Follows the same conventions as the rest of the suite: unittest.TestCase, a
self-contained FakeLLM/FakeResponse stand-in for ChatGroq and for the shared
RAG node (patched onto backend.app.agents.support_agent.nodes), and a shared
_initial_state helper -- no Support Agent source files are modified.

Run with: python -m unittest test_support_agent_sample_tickets.py -v
"""
import json
import re
import unittest
from unittest.mock import patch

from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.agents.support_agent.graph import build_support_graph

_TICKET_ID_PATTERN = re.compile(r"^TCK-[0-9A-F]{8}$")

_UNKNOWN_INTENT_RESPONSE = (
    "I can currently help with password resets, order status, and "
    "refund requests. Could you clarify which of these you need help with?"
)
_PASSWORD_RESET_RESPONSE = "A password reset link has been sent to your account email."
_ORDER_STATUS_RESPONSE = "Your order is currently being processed."
_REFUND_RESPONSE = "Your refund request has been submitted for manual review."


# Each entry is the single source of truth for both what FakeLLM returns and
# what the test asserts: `raw_category`/`confidence` are what the (fake) LLM
# proposes for ticket_classification_node; `expected_ticket_category` is what
# should actually land in state *after* the node's real threshold-gating
# logic runs on that raw value -- for most entries these are the same, but
# for the low-confidence "Unknown Requests" entries below they intentionally
# differ, exercising the real gating code rather than bypassing it.
SAMPLE_TICKETS = [
    # --- Refund ---
    dict(
        name="refund_broken_item",
        user_input="I'd like a refund for order #4521, it arrived broken and I don't want a replacement.",
        raw_category="Refund", confidence=0.93,
        expected_ticket_category="Refund",
        expected_workflow="refund_request",
        expected_response=_REFUND_RESPONSE,
    ),
    dict(
        name="refund_money_back",
        user_input="Can I get my money back for the shoes I sent back last week?",
        raw_category="Refund", confidence=0.88,
        expected_ticket_category="Refund",
        expected_workflow="refund_request",
        expected_response=_REFUND_RESPONSE,
    ),
    dict(
        name="refund_not_as_advertised",
        user_input="This product doesn't work as advertised, I want a full refund please.",
        raw_category="Refund", confidence=0.9,
        expected_ticket_category="Refund",
        expected_workflow="refund_request",
        expected_response=_REFUND_RESPONSE,
    ),
    # --- Password Reset ---
    dict(
        name="password_forgot_locked_out",
        user_input="I forgot my password and I'm locked out of my account.",
        raw_category="Password Reset", confidence=0.95,
        expected_ticket_category="Password Reset",
        expected_workflow="password_reset",
        expected_response=_PASSWORD_RESET_RESPONSE,
    ),
    dict(
        name="password_cant_log_in",
        user_input="I can't log in, it keeps saying my password is incorrect.",
        raw_category="Password Reset", confidence=0.91,
        expected_ticket_category="Password Reset",
        expected_workflow="password_reset",
        expected_response=_PASSWORD_RESET_RESPONSE,
    ),
    dict(
        name="password_no_reset_email",
        user_input="Please reset my password, I never received the reset email.",
        raw_category="Password Reset", confidence=0.9,
        expected_ticket_category="Password Reset",
        expected_workflow="password_reset",
        expected_response=_PASSWORD_RESET_RESPONSE,
    ),
    # --- Billing (no dedicated workflow branch -> routes to unknown) ---
    dict(
        name="billing_charged_twice",
        user_input="I was charged twice for my subscription this month, please fix my invoice.",
        raw_category="Billing", confidence=0.82,
        expected_ticket_category="Billing",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="billing_update_card",
        user_input="Can you update the credit card on file for my monthly billing?",
        raw_category="Billing", confidence=0.79,
        expected_ticket_category="Billing",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="billing_unrecognized_charge",
        user_input="My latest invoice shows an extra charge I don't recognize.",
        raw_category="Billing", confidence=0.8,
        expected_ticket_category="Billing",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    # --- Technical Issue (no dedicated workflow branch -> routes to unknown) ---
    dict(
        name="technical_app_crashing",
        user_input="The app keeps crashing every time I try to upload a photo.",
        raw_category="Technical Issue", confidence=0.85,
        expected_ticket_category="Technical Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="technical_500_error",
        user_input="Your website throws a 500 error when I try to check out.",
        raw_category="Technical Issue", confidence=0.83,
        expected_ticket_category="Technical Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="technical_dashboard_wont_load",
        user_input="The dashboard won't load no matter which browser I use.",
        raw_category="Technical Issue", confidence=0.81,
        expected_ticket_category="Technical Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    # --- Account Issue (no dedicated workflow branch -> routes to unknown) ---
    dict(
        name="account_merge_two_accounts",
        user_input="I need to merge my two accounts into one.",
        raw_category="Account Issue", confidence=0.74,
        expected_ticket_category="Account Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="account_change_username",
        user_input="How do I change the username on my account?",
        raw_category="Account Issue", confidence=0.72,
        expected_ticket_category="Account Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="account_update_shipping_address",
        user_input="Can you update the shipping address saved on my account profile?",
        raw_category="Account Issue", confidence=0.7,
        expected_ticket_category="Account Issue",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    # --- Order Status ---
    dict(
        name="order_status_tracking_blank",
        user_input="Where is my order? The tracking page shows nothing.",
        raw_category="Order Status", confidence=0.92,
        expected_ticket_category="Order Status",
        expected_workflow="order_status",
        expected_response=_ORDER_STATUS_RESPONSE,
    ),
    dict(
        name="order_status_delivery_update",
        user_input="Can you give me a delivery update for order #7788?",
        raw_category="Order Status", confidence=0.89,
        expected_ticket_category="Order Status",
        expected_workflow="order_status",
        expected_response=_ORDER_STATUS_RESPONSE,
    ),
    dict(
        name="order_status_late_package",
        user_input="My package was supposed to arrive yesterday, can you track it for me?",
        raw_category="Order Status", confidence=0.87,
        expected_ticket_category="Order Status",
        expected_workflow="order_status",
        expected_response=_ORDER_STATUS_RESPONSE,
    ),
    # --- General Inquiry (confidently general -> stays General Inquiry,
    # no dedicated workflow branch -> routes to unknown) ---
    dict(
        name="general_inquiry_ships_internationally",
        user_input="Do you ship internationally?",
        raw_category="General Inquiry", confidence=0.75,
        expected_ticket_category="General Inquiry",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="general_inquiry_support_hours",
        user_input="What are your customer support hours?",
        raw_category="General Inquiry", confidence=0.8,
        expected_ticket_category="General Inquiry",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="general_inquiry_paypal",
        user_input="Do you accept PayPal for purchases?",
        raw_category="General Inquiry", confidence=0.7,
        expected_ticket_category="General Inquiry",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    # --- Unknown Requests: off-topic or too vague to classify confidently.
    # raw_category is what the (fake) LLM guesses, but confidence is
    # deliberately below _TICKET_CATEGORY_CONFIDENCE_THRESHOLD (0.6), so
    # ticket_classification_node's real gating logic downgrades it to
    # "Unknown" -- these double as the low-confidence coverage.
    dict(
        name="unknown_off_topic_weather",
        user_input="What's the weather like today?",
        raw_category="General Inquiry", confidence=0.35,
        expected_ticket_category="Unknown",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="unknown_gibberish",
        user_input="asdkfjaslkdfj random gibberish text 12345",
        raw_category="General Inquiry", confidence=0.2,
        expected_ticket_category="Unknown",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="unknown_too_vague",
        user_input="I have a question about my thing, can you help?",
        raw_category="General Inquiry", confidence=0.35,
        expected_ticket_category="Unknown",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
    dict(
        name="unknown_no_idea_who_to_ask",
        user_input="Not sure who to ask about this but I really need some help.",
        raw_category="General Inquiry", confidence=0.3,
        expected_ticket_category="Unknown",
        expected_workflow="unknown",
        expected_response=_UNKNOWN_INTENT_RESPONSE,
    ),
]


class FakeResponse:
    def __init__(self, content):
        self.content = content


def _find_ticket(lowered_prompt: str) -> dict:
    """Locate which SAMPLE_TICKETS entry a prompt is about, from the
    trailing "User message:" section -- same slicing rationale as the
    intent-classifier branches in the other Support Agent test files: the
    category/workflow descriptions earlier in the prompt already contain
    lots of overlapping keywords, so only the literal user message is a
    reliable match target."""
    user_message = lowered_prompt.rsplit("user message:", 1)[-1]
    for ticket in SAMPLE_TICKETS:
        if ticket["user_input"].lower() in user_message:
            return ticket
    raise AssertionError(f"No sample ticket matches prompt tail: {user_message!r}")


class FakeLLM:
    """Deterministic stand-in for ChatGroq. SAMPLE_TICKETS is the single
    source of truth for both what this returns and what the test asserts,
    so there's no risk of the fake and the expectations drifting apart."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "ticket classification system" in lowered:
            ticket = _find_ticket(lowered)
            return FakeResponse(
                json.dumps({"category": ticket["raw_category"], "confidence": ticket["confidence"]})
            )

        if "intent classifier" in lowered:
            ticket = _find_ticket(lowered)
            return FakeResponse(ticket["expected_workflow"])

        if "helping a user reset their password" in lowered:
            return FakeResponse(_PASSWORD_RESET_RESPONSE)

        if "answering an order status question" in lowered:
            return FakeResponse(_ORDER_STATUS_RESPONSE)

        if "processing a refund request" in lowered:
            return FakeResponse(_REFUND_RESPONSE)

        raise AssertionError(f"FakeLLM received an unexpected prompt: {prompt!r}")


def _fake_rag_retrieval_node(state: dict) -> dict:
    """Deterministic stand-in for core.rag_node.rag_retrieval_node -- avoids
    hitting the real embedding model / pgvector DB in tests."""
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


class SampleTicketDataTests(unittest.TestCase):
    """Sanity checks on the dataset itself, independent of the graph."""

    def test_at_least_twenty_tickets(self):
        self.assertGreaterEqual(len(SAMPLE_TICKETS), 20)

    def test_all_seven_categories_plus_unknown_are_represented(self):
        categories = {t["expected_ticket_category"] for t in SAMPLE_TICKETS}
        expected = {
            "Refund", "Password Reset", "Billing", "Technical Issue",
            "Account Issue", "Order Status", "General Inquiry", "Unknown",
        }
        self.assertEqual(categories, expected)

    def test_ticket_names_are_unique(self):
        names = [t["name"] for t in SAMPLE_TICKETS]
        self.assertEqual(len(names), len(set(names)))


class SampleTicketGraphTests(unittest.TestCase):
    """Runs every sample ticket through the real compiled graph and checks
    the full expected shape: ticket category, workflow routing, and final
    response -- plus that a ticket record is always created regardless of
    category."""

    def setUp(self):
        patcher = patch.object(support_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)

        rag_patcher = patch.object(
            support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
        )
        rag_patcher.start()
        self.addCleanup(rag_patcher.stop)

        self.graph = build_support_graph()

    def test_sample_tickets_match_expected_category_workflow_and_response(self):
        for ticket in SAMPLE_TICKETS:
            with self.subTest(ticket=ticket["name"]):
                result = self.graph.invoke(_initial_state(ticket["user_input"]))

                self.assertEqual(result["ticket_category"], ticket["expected_ticket_category"])
                self.assertEqual(result["workflow"], ticket["expected_workflow"])
                self.assertEqual(result["agent_response"], ticket["expected_response"])

                # Every ticket gets a real record, regardless of category.
                self.assertRegex(result["ticket_id"], _TICKET_ID_PATTERN)
                self.assertEqual(result["ticket_status"], "Open")
                self.assertIsInstance(result.get("ticket_category_confidence"), float)


if __name__ == "__main__":
    unittest.main()
