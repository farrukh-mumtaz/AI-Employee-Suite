"""
Comprehensive Support Agent test suite.

Complements the existing Support Agent tests rather than duplicating them:
    - test_support_agent_graph.py         -- end-to-end happy-path workflows
    - test_support_agent_nodes.py         -- ticket_intake_node unit tests
    - test_support_agent_sample_tickets.py -- >=20 realistic tickets end-to-end

This file adds the gaps: explicit graph-compilation checks, dedicated unit
tests for ticket_classification_node (categories, confidence gating, low
confidence, malformed/unrecognized LLM output) and retrieve_refund_policy_node
(RAG success/failure) that aren't exercised in isolation elsewhere,
invalid/missing/empty/unicode input handling at the full-graph level, a
dedicated unknown-intent check, and state isolation across repeated
invocations of the same compiled graph. Mirrors test_hr_agent_comprehensive.py.

Follows the same conventions as the rest of the suite: unittest.TestCase, a
self-contained FakeLLM/FakeResponse stand-in for ChatGroq, and a shared
_initial_state helper -- no Support Agent source files are modified.

Run with: python -m unittest test_support_agent_comprehensive.py -v
"""
import json
import unittest
from unittest.mock import patch

from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.agents.support_agent.graph import build_support_graph
from backend.app.agents.support_agent.rag import lookup_order_status

_UNKNOWN_INTENT_RESPONSE = (
    "I can currently help with password resets, order status checks, "
    "and submitting new refund requests. I'm not yet able to answer "
    "general policy questions or check the status of an existing "
    "request -- please reach out to support directly for those. "
    "Could you tell me more about what you need?"
)


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Deterministic stand-in for ChatGroq, mirroring the FakeLLM used in
    test_support_agent_graph.py so end-to-end behavior stays consistent
    across both files."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "ticket classification system" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message or "log in" in user_message:
                return FakeResponse(json.dumps({"category": "Password Reset", "confidence": 0.9}))
            if "refund" in user_message or "return" in user_message or "money back" in user_message:
                return FakeResponse(json.dumps({"category": "Refund", "confidence": 0.9}))
            if "order" in user_message or "delivery" in user_message or "track" in user_message:
                return FakeResponse(json.dumps({"category": "Order Status", "confidence": 0.9}))
            return FakeResponse(json.dumps({"category": "General Inquiry", "confidence": 0.4}))

        if "intent classifier" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "password" in user_message or "locked out" in user_message or "log in" in user_message:
                return FakeResponse("password_reset")
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
    updated = dict(state)
    updated["system_prompt"] = (
        "You are a helpful AI assistant.\n\n"
        "Relevant company information:\nRefunds are eligible within 30 days of purchase."
    )
    return updated


def _initial_state(user_input) -> dict:
    return {
        "messages": [],
        "user_input": user_input,
        "agent_response": None,
        "agent_name": "support_agent",
    }


class GraphCompilationTests(unittest.TestCase):
    """Graph construction/compilation should be deterministic, cheap to
    repeat, and expose the node wiring described in graph.py's docstring."""

    def test_build_support_graph_compiles_without_error(self):
        graph = build_support_graph()
        self.assertIsNotNone(graph)

    def test_build_support_graph_is_repeatable_and_independent(self):
        first = build_support_graph()
        second = build_support_graph()
        self.assertIsNot(first, second)

    def test_compiled_graph_contains_all_expected_nodes(self):
        graph = build_support_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "ticket_intake",
            "ticket_classification",
            "classify_intent",
            "extract_account_details",
            "send_password_reset",
            "extract_order_details",
            "retrieve_order_status",
            "generate_order_status_response",
            "extract_refund_details",
            "retrieve_refund_policy",
            "evaluate_refund_request",
            "unknown_intent",
        }
        self.assertTrue(expected.issubset(node_names))


class LookupOrderStatusTests(unittest.TestCase):
    """Direct unit tests for rag.py's remaining function (order-status
    lookup), which had no dedicated coverage elsewhere in the suite."""

    def test_valid_order_id_returns_processing_placeholder(self):
        self.assertEqual(
            lookup_order_status("ORD-123"), "Processing -- status lookup not yet integrated"
        )

    def test_none_order_id_returns_unknown(self):
        self.assertEqual(lookup_order_status(None), "Unknown -- no order ID provided")

    def test_unspecified_order_id_returns_unknown(self):
        self.assertEqual(lookup_order_status("Unspecified"), "Unknown -- no order ID provided")


class RagRetrievalNodeTests(unittest.TestCase):
    """Direct unit tests for retrieve_refund_policy_node's delegation to the
    shared RAG node (backend/app/core/rag_node.py) -- success and failure
    paths, isolated from the rest of the graph."""

    def test_success_merges_system_prompt_from_shared_rag_node(self):
        with patch.object(
            support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
        ):
            result = support_nodes.retrieve_refund_policy_node(
                {"user_input": "I want a refund", "order_id": "ORD-1"}
            )
        self.assertIn("Refunds are eligible within 30 days", result["system_prompt"])

    def test_shared_rag_node_failure_degrades_gracefully(self):
        # A retrieval/embedding failure (network, DB, model load, ...) must
        # not crash the node -- it should log and return no update at all,
        # letting the graph continue with no policy context.
        with patch.object(
            support_nodes, "rag_retrieval_node", side_effect=RuntimeError("embedding backend down")
        ):
            result = support_nodes.retrieve_refund_policy_node(
                {"user_input": "I want a refund", "order_id": "ORD-1"}
            )
        self.assertEqual(result, {})

    def test_downstream_prompt_falls_back_to_empty_context_after_failure(self):
        # evaluate_refund_request_node reads system_prompt via `or ""`, so a
        # retrieval failure upstream must not raise a KeyError/format error.
        with patch.object(support_nodes, "get_llm", return_value=FakeLLM()):
            state = {
                "user_input": "I want a refund, it broke",
                "order_id": "Unspecified",
                "refund_reason": "Unspecified",
            }
            result = support_nodes.evaluate_refund_request_node(state)
        self.assertEqual(result["refund_decision"], "pending_manual_review")
        self.assertIsNotNone(result["agent_response"])


class _SingleResponseLLM:
    """Stand-in for ChatGroq that always returns the same canned response,
    regardless of prompt -- for tests that only care about how
    ticket_classification_node parses one specific LLM response."""

    def __init__(self, content):
        self._content = content

    def invoke(self, prompt: str) -> FakeResponse:
        return FakeResponse(self._content)


class TicketClassificationNodeTests(unittest.TestCase):
    """Direct unit tests for ticket_classification_node: every recognized
    category, the confidence threshold boundary, low-confidence downgrade,
    unrecognized/malformed LLM output, and the no-LLM-call empty-input path."""

    def _classify(self, user_input, llm_response_json):
        with patch.object(
            support_nodes, "get_llm", return_value=_SingleResponseLLM(llm_response_json)
        ):
            return support_nodes.ticket_classification_node({"user_input": user_input})

    def test_each_recognized_category_is_returned_as_is_above_threshold(self):
        for category in (
            "Refund", "Password Reset", "Billing", "Technical Issue",
            "Account Issue", "Order Status", "General Inquiry",
        ):
            with self.subTest(category=category):
                result = self._classify(
                    "some ticket text",
                    json.dumps({"category": category, "confidence": 0.75}),
                )
                self.assertEqual(result["ticket_category"], category)
                self.assertEqual(result["ticket_category_confidence"], 0.75)

    def test_confidence_exactly_at_threshold_is_not_downgraded(self):
        # _TICKET_CATEGORY_CONFIDENCE_THRESHOLD is 0.6; the gate is `< threshold`,
        # so exactly-at-threshold must still pass.
        threshold = support_nodes._TICKET_CATEGORY_CONFIDENCE_THRESHOLD
        result = self._classify(
            "some ticket text", json.dumps({"category": "Billing", "confidence": threshold})
        )
        self.assertEqual(result["ticket_category"], "Billing")

    def test_confidence_just_below_threshold_is_downgraded_to_unknown(self):
        threshold = support_nodes._TICKET_CATEGORY_CONFIDENCE_THRESHOLD
        result = self._classify(
            "some ticket text",
            json.dumps({"category": "Billing", "confidence": threshold - 0.01}),
        )
        self.assertEqual(result["ticket_category"], "Unknown")
        self.assertEqual(result["ticket_category_confidence"], threshold - 0.01)

    def test_zero_confidence_is_downgraded_to_unknown(self):
        result = self._classify(
            "some ticket text", json.dumps({"category": "Refund", "confidence": 0.0})
        )
        self.assertEqual(result["ticket_category"], "Unknown")

    def test_unrecognized_category_is_downgraded_to_unknown_even_with_high_confidence(self):
        result = self._classify(
            "some ticket text",
            json.dumps({"category": "Something Else Entirely", "confidence": 0.99}),
        )
        self.assertEqual(result["ticket_category"], "Unknown")

    def test_malformed_json_response_defaults_to_unknown(self):
        result = self._classify("some ticket text", "not valid json at all")
        self.assertEqual(result["ticket_category"], "Unknown")
        self.assertEqual(result["ticket_category_confidence"], 0.0)

    def test_missing_fields_in_json_response_default_to_unknown(self):
        result = self._classify("some ticket text", json.dumps({}))
        self.assertEqual(result["ticket_category"], "Unknown")
        self.assertEqual(result["ticket_category_confidence"], 0.0)

    def test_get_llm_construction_failure_defaults_to_unknown_without_raising(self):
        # Regression test: get_llm() itself can raise (e.g. missing/invalid
        # GROQ_API_KEY raises groq.GroqError at ChatGroq construction time,
        # before .invoke() is ever reached) -- distinct from .invoke() or
        # json.loads() raising, which the other tests in this class already
        # cover. Every other LLM-calling node degrades gracefully via
        # _invoke_llm(), which wraps get_llm() in its try/except; this node
        # must do the same instead of letting the graph invocation crash.
        with patch.object(
            support_nodes, "get_llm", side_effect=RuntimeError("api_key client option must be set")
        ):
            result = support_nodes.ticket_classification_node({"user_input": "some ticket text"})
        self.assertEqual(result, {"ticket_category": "Unknown", "ticket_category_confidence": 0.0})

    def test_empty_user_input_returns_unknown_without_calling_llm(self):
        def _fail_if_called():
            raise AssertionError("get_llm should not be called for empty user_input")

        with patch.object(support_nodes, "get_llm", side_effect=_fail_if_called):
            result = support_nodes.ticket_classification_node({"user_input": ""})
        self.assertEqual(result, {"ticket_category": "Unknown", "ticket_category_confidence": 0.0})

    def test_whitespace_only_user_input_returns_unknown_without_calling_llm(self):
        def _fail_if_called():
            raise AssertionError("get_llm should not be called for whitespace-only user_input")

        with patch.object(support_nodes, "get_llm", side_effect=_fail_if_called):
            result = support_nodes.ticket_classification_node({"user_input": "   \n\t  "})
        self.assertEqual(result, {"ticket_category": "Unknown", "ticket_category_confidence": 0.0})

    def test_missing_user_input_key_returns_unknown_without_raising(self):
        def _fail_if_called():
            raise AssertionError("get_llm should not be called when user_input is missing")

        with patch.object(support_nodes, "get_llm", side_effect=_fail_if_called):
            result = support_nodes.ticket_classification_node({})
        self.assertEqual(result, {"ticket_category": "Unknown", "ticket_category_confidence": 0.0})


class GraphInvalidAndEmptyInputTests(unittest.TestCase):
    """Full-graph behavior for missing, empty, malformed, or unusual input
    -- the graph must never raise, and must fall back to the unknown branch
    (both workflow and ticket_category) when there's nothing usable to
    classify."""

    def setUp(self):
        patcher = patch.object(support_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)

        # test_very_long_input_does_not_raise below uses refund-flavored
        # text, which reaches retrieve_refund_policy_node -- must be mocked
        # like every other graph-invoking test class, or it hits the real
        # embedding model / pgvector DB.
        rag_patcher = patch.object(
            support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
        )
        rag_patcher.start()
        self.addCleanup(rag_patcher.stop)

        self.graph = build_support_graph()

    def test_missing_user_input_key_does_not_raise(self):
        state = {"messages": [], "agent_response": None, "agent_name": "support_agent"}
        result = self.graph.invoke(state)
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["ticket_category"], "Unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_none_user_input_does_not_raise(self):
        result = self.graph.invoke(_initial_state(None))
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["ticket_category"], "Unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_empty_string_input_routes_to_unknown(self):
        result = self.graph.invoke(_initial_state(""))
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["ticket_category"], "Unknown")

    def test_whitespace_only_input_routes_to_unknown(self):
        result = self.graph.invoke(_initial_state("   \n\t  "))
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["ticket_category"], "Unknown")

    def test_numeric_only_input_does_not_raise(self):
        result = self.graph.invoke(_initial_state("123456789"))
        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_unicode_and_emoji_input_does_not_raise(self):
        result = self.graph.invoke(
            _initial_state("パスワードをリセットしてください 🔒 forgot my password, locked out")
        )
        self.assertEqual(result["workflow"], "password_reset")
        self.assertIsNotNone(result["agent_response"])

    def test_very_long_input_does_not_raise(self):
        long_input = "I want a refund for my order, it arrived broken. " * 500
        result = self.graph.invoke(_initial_state(long_input))
        self.assertEqual(result["workflow"], "refund_request")
        self.assertIsNotNone(result["agent_response"])

    def test_ticket_is_still_created_for_every_invalid_input_case(self):
        for user_input in (None, "", "   ", "123456789"):
            with self.subTest(user_input=user_input):
                result = self.graph.invoke(_initial_state(user_input))
                self.assertIsNotNone(result.get("ticket_id"))
                self.assertEqual(result.get("ticket_status"), "Open")


class UnknownIntentTests(unittest.TestCase):
    """Dedicated coverage for the unknown-intent fallback branch: the exact
    clarification message, and that it's reached regardless of
    ticket_category (only `workflow` drives routing)."""

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

    def test_unknown_intent_node_returns_exact_clarification_message(self):
        result = support_nodes.unknown_intent_node({})
        self.assertEqual(result["agent_response"], _UNKNOWN_INTENT_RESPONSE)

    def test_off_topic_message_routes_to_unknown_with_no_llm_error(self):
        result = self.graph.invoke(_initial_state("What's the weather like today?"))
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["agent_response"], _UNKNOWN_INTENT_RESPONSE)

    def test_billing_style_message_has_a_real_category_but_unknown_workflow(self):
        # Billing has no dedicated workflow branch -- ticket_category and
        # workflow are independent, per ticket_classification_node's design.
        result = self.graph.invoke(
            _initial_state("I was charged twice for my subscription, please fix my invoice.")
        )
        self.assertEqual(result["workflow"], "unknown")
        self.assertEqual(result["agent_response"], _UNKNOWN_INTENT_RESPONSE)
        self.assertIsNotNone(result.get("ticket_category"))


class EndToEndGraphFlowTests(unittest.TestCase):
    """Full-state sanity checks across every branch, independent of which
    one ran -- complements the per-branch tests in test_support_agent_graph.py
    and test_support_agent_sample_tickets.py by checking the whole picture
    (base AgentState fields + ticket fields + classification fields
    together) rather than one field at a time."""

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

    def test_base_agent_state_and_ticket_fields_survive_every_branch(self):
        for user_input in (
            "I forgot my password and I'm locked out.",
            "Where is my order? Tracking shows nothing.",
            "I want a refund, my order arrived broken.",
            "What's the weather like today?",
        ):
            with self.subTest(user_input=user_input):
                result = self.graph.invoke(_initial_state(user_input))
                self.assertEqual(result["user_input"], user_input)
                self.assertEqual(result["agent_name"], "support_agent")
                self.assertEqual(result["messages"], [])
                self.assertIsNotNone(result["agent_response"])
                self.assertIn("workflow", result)
                self.assertIn("ticket_category", result)
                self.assertIn("ticket_category_confidence", result)
                self.assertIsNotNone(result["ticket_id"])
                self.assertEqual(result["ticket_status"], "Open")

    def test_ticket_classification_runs_before_workflow_fork_for_every_branch(self):
        # ticket_category/confidence must always be present by the time the
        # graph reaches END, regardless of which workflow branch ran --
        # proof that ticket_classification sits before the fork, not inside
        # one specific branch.
        for user_input in (
            "I forgot my password.",
            "Where is my order?",
            "I want a refund.",
            "Some unrelated message.",
        ):
            with self.subTest(user_input=user_input):
                result = self.graph.invoke(_initial_state(user_input))
                self.assertIsNotNone(result.get("ticket_category"))
                self.assertIsInstance(result.get("ticket_category_confidence"), float)


class StateIsolationTests(unittest.TestCase):
    """A single compiled graph instance is reused across multiple invoke()
    calls in production -- state from one invocation must never leak into
    the next."""

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

    def test_password_reset_then_order_status_do_not_leak_state(self):
        password_result = self.graph.invoke(
            _initial_state("I forgot my password and I'm locked out.")
        )
        self.assertEqual(password_result["workflow"], "password_reset")

        order_result = self.graph.invoke(_initial_state("Where is my order? Tracking shows nothing."))
        self.assertEqual(order_result["workflow"], "order_status")
        # Fields set by the previous (password reset) invocation must not
        # reappear in this unrelated order-status result.
        self.assertIsNone(order_result.get("reset_link_sent"))
        self.assertIsNone(order_result.get("account_email"))

    def test_refund_then_password_reset_do_not_leak_ticket_ids(self):
        refund_result = self.graph.invoke(_initial_state("I want a refund, my order arrived broken."))
        password_result = self.graph.invoke(_initial_state("I forgot my password."))
        self.assertNotEqual(refund_result["ticket_id"], password_result["ticket_id"])

    def test_repeated_invocations_produce_distinct_result_dicts(self):
        first = self.graph.invoke(_initial_state("I forgot my password."))
        second = self.graph.invoke(_initial_state("I forgot my password."))
        self.assertIsNot(first, second)
        self.assertNotEqual(first["ticket_id"], second["ticket_id"])


if __name__ == "__main__":
    unittest.main()
