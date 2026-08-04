# LLM-failure resilience tests for the Support Agent
# (backend/app/agents/support_agent/nodes.py).
#
# Bug fixed: every LLM-calling node except ticket_classification_node used
# to call `llm.invoke()` directly with no error handling, so a transient
# Groq failure (network error, bad/missing API key, provider outage, rate
# limiting) would crash the entire graph invocation. hr_agent/nodes.py
# already centralized this via `_invoke_llm()` with a deterministic
# fallback string (see test_hr_agent_nodes.py's RaisingLLM tests); this file
# is the Support Agent equivalent, added when nodes.py was updated to use
# the same `_invoke_llm()` pattern.
#
# Run with: python -m pytest test_support_agent_resilience.py -v
import unittest
from unittest.mock import patch

from backend.app.agents.support_agent import nodes


class RaisingLLM:
    """Stands in for an LLM client whose call fails (network error, bad
    API key, provider outage, etc.). Mirrors test_hr_agent_nodes.py's
    RaisingLLM."""

    def invoke(self, prompt):
        raise RuntimeError("simulated LLM/network failure")


class EmptyResponseLLM:
    """Stands in for an LLM client that returns a response with no usable
    content (e.g. an empty string) -- must be treated the same as a raised
    exception, not passed through as the agent's response."""

    class _Response:
        content = "   "

    def invoke(self, prompt):
        return self._Response()


class ClassifyIntentNodeResilienceTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_llm_failure_falls_back_to_unknown_workflow(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.classify_intent_node({"user_input": "I forgot my password."})
        self.assertEqual(result, {"workflow": "unknown"})

    @patch.object(nodes, "get_llm")
    def test_empty_input_skips_llm_call_entirely(self, mock_get_llm):
        result = nodes.classify_intent_node({"user_input": "   "})
        self.assertEqual(result, {"workflow": "unknown"})
        mock_get_llm.assert_not_called()


class SendPasswordResetNodeResilienceTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_llm_failure_still_returns_a_response_and_marks_link_sent(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.send_password_reset_node({"account_email": "jane@example.com"})
        self.assertTrue(result["reset_link_sent"])
        self.assertIn("jane@example.com", result["agent_response"])

    @patch.object(nodes, "get_llm")
    def test_empty_llm_response_falls_back(self, mock_get_llm):
        mock_get_llm.return_value = EmptyResponseLLM()
        result = nodes.send_password_reset_node({"account_email": "Unknown"})
        self.assertTrue(result["reset_link_sent"])
        self.assertTrue(result["agent_response"])


class GenerateOrderStatusResponseNodeResilienceTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_llm_failure_still_returns_a_response(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.generate_order_status_response_node(
            {"order_id": "ORD-1", "order_status": "Shipped", "user_input": "Where is my order?"}
        )
        self.assertIn("ORD-1", result["agent_response"])
        self.assertIn("Shipped", result["agent_response"])

    @patch.object(nodes, "get_llm")
    def test_missing_user_input_key_does_not_raise(self, mock_get_llm):
        # Regression test: this node used to index state["user_input"]
        # directly, which would KeyError if the key were ever absent.
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.generate_order_status_response_node(
            {"order_id": "ORD-1", "order_status": "Shipped"}
        )
        self.assertTrue(result["agent_response"])


class EvaluateRefundRequestNodeResilienceTests(unittest.TestCase):
    @patch.object(nodes, "get_llm")
    def test_llm_failure_still_returns_pending_manual_review(self, mock_get_llm):
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.evaluate_refund_request_node(
            {"order_id": "ORD-1", "refund_reason": "arrived broken", "user_input": "refund please"}
        )
        self.assertEqual(result["refund_decision"], "pending_manual_review")
        self.assertTrue(result["agent_response"])

    @patch.object(nodes, "get_llm")
    def test_missing_user_input_key_does_not_raise(self, mock_get_llm):
        # Regression test: this node used to index state["user_input"]
        # directly, which would KeyError if the key were ever absent.
        mock_get_llm.return_value = RaisingLLM()
        result = nodes.evaluate_refund_request_node({"order_id": "ORD-1"})
        self.assertEqual(result["refund_decision"], "pending_manual_review")
        self.assertTrue(result["agent_response"])


class ExtractionNodesDoNotOverwriteExistingFieldsTests(unittest.TestCase):
    """Regression tests for the switch from `state.setdefault(...)` (which
    only checks key *presence*) to a truthiness check matching hr_agent's
    convention (which also refills an existing-but-empty value)."""

    def test_extract_account_details_preserves_pre_supplied_email(self):
        result = nodes.extract_account_details_node({"account_email": "jane@example.com"})
        self.assertEqual(result, {})

    def test_extract_account_details_fills_missing_email(self):
        result = nodes.extract_account_details_node({})
        self.assertEqual(result, {"account_email": "Unknown"})

    def test_extract_order_details_preserves_pre_supplied_order_id(self):
        result = nodes.extract_order_details_node({"order_id": "ORD-42"})
        self.assertEqual(result, {})

    def test_extract_refund_details_preserves_pre_supplied_fields(self):
        result = nodes.extract_refund_details_node(
            {"order_id": "ORD-42", "refund_reason": "wrong size"}
        )
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
