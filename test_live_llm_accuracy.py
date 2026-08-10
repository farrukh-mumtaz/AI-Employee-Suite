# Live-LLM accuracy tests for HR Agent + Support Agent intent classification,
# and cross-agent routing isolation.
#
# Every other test file in this repo stubs the LLM with a deterministic
# FakeLLM, which is the right choice for testing graph wiring/node logic --
# but it means none of them can catch a real *prompt accuracy* regression,
# since FakeLLM always does exactly what the test author told it to do. The
# bugs fixed in this change (HR: "what's our policy on parental leave?"
# misrouted to leave_request and answered as if a request had been
# submitted; Support: "what's your return policy?" misrouted to
# refund_request and silently created a phantom pending-review refund
# ticket) were only found by running the real Groq LLM against realistic
# input and reading the output -- so this file locks that fix in against a
# regression, using the real model.
#
# Skipped automatically when GROQ_API_KEY is not set (e.g. in CI without
# secrets configured) so it never blocks a run that can't reach the LLM.
# Non-deterministic by nature (real model output) -- kept small and focused
# on the specific classification boundary that was buggy, not a full
# behavioral suite (that's what the FakeLLM-based files are for).
#
# Run with: python -m pytest test_live_llm_accuracy.py -v
import os
import unittest
from unittest.mock import patch

from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.agents.support_agent import nodes as support_nodes
from backend.app.agents.support_agent.graph import build_support_graph

_HAS_GROQ_KEY = bool(os.getenv("GROQ_API_KEY"))


def _fake_rag_retrieval_node(state: dict) -> dict:
    # Refund-policy retrieval needs a real pgvector/Postgres store and
    # downloads a multi-GB embedding model on first use -- stub it out so
    # this file only exercises classify_intent_node against the real LLM,
    # not the unrelated RAG pipeline.
    updated = dict(state)
    updated["system_prompt"] = "Refunds are eligible within 30 days of purchase."
    return updated


def _hr_workflow(text: str) -> str:
    graph = build_hr_graph()
    result = graph.invoke(
        {"messages": [], "user_input": text, "agent_response": None, "agent_name": "hr_agent"}
    )
    return result.get("workflow")


def _support_workflow(text: str) -> str:
    with patch.object(
        support_nodes, "rag_retrieval_node", side_effect=_fake_rag_retrieval_node
    ):
        graph = build_support_graph()
        result = graph.invoke(
            {
                "messages": [],
                "user_input": text,
                "agent_response": None,
                "agent_name": "support_agent",
            }
        )
    return result.get("workflow")


@unittest.skipUnless(_HAS_GROQ_KEY, "GROQ_API_KEY not set -- skipping live-LLM accuracy tests")
class HRIntentClassificationAccuracyTests(unittest.TestCase):
    """Regression coverage for the CLASSIFY_INTENT_PROMPT tightening in
    hr_agent/prompts.py: policy/balance/status questions about leave must
    NOT be routed into the leave_request submission workflow."""

    def test_policy_question_is_not_misrouted_to_leave_request(self):
        self.assertEqual(_hr_workflow("What's our policy on parental leave?"), "unknown")

    def test_balance_question_is_not_misrouted_to_leave_request(self):
        self.assertEqual(_hr_workflow("How many vacation days do I have left?"), "unknown")

    def test_genuine_leave_request_still_classified_correctly(self):
        # Guards against an overcorrection that would break the real workflow.
        self.assertEqual(
            _hr_workflow("Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure."),
            "leave_request",
        )

    def test_genuine_onboarding_request_still_classified_correctly(self):
        self.assertEqual(
            _hr_workflow("Please onboard John Doe as a Backend Engineer starting next week"),
            "onboarding",
        )


@unittest.skipUnless(_HAS_GROQ_KEY, "GROQ_API_KEY not set -- skipping live-LLM accuracy tests")
class SupportIntentClassificationAccuracyTests(unittest.TestCase):
    """Regression coverage for the CLASSIFY_INTENT_PROMPT tightening in
    support_agent/prompts.py: general policy questions must NOT be routed
    into the refund_request (transactional, ticket-creating) workflow."""

    def test_policy_question_is_not_misrouted_to_refund_request(self):
        self.assertEqual(_support_workflow("Just wondering what your return policy is."), "unknown")

    def test_genuine_refund_request_still_classified_correctly(self):
        self.assertEqual(
            _support_workflow("I'd like a refund for order #4521, it arrived broken."),
            "refund_request",
        )

    def test_genuine_password_reset_still_classified_correctly(self):
        self.assertEqual(
            _support_workflow("I forgot my password and I'm locked out of my account."),
            "password_reset",
        )


@unittest.skipUnless(_HAS_GROQ_KEY, "GROQ_API_KEY not set -- skipping live-LLM cross-routing tests")
class CrossAgentRoutingIsolationLiveTests(unittest.TestCase):
    """Confirms each agent's intent classifier stays within its own domain
    against the real LLM: a Support-domain message sent through the HR
    graph, and an HR-domain message sent through the Support graph, must
    both fall back to "unknown" rather than being (mis)classified into a
    workflow that belongs to the other agent."""

    def test_support_domain_message_is_unknown_to_hr_agent(self):
        self.assertEqual(
            _hr_workflow("I'd like a refund for order #4521, it arrived broken."), "unknown"
        )
        self.assertEqual(
            _hr_workflow("I forgot my password and I'm locked out of my account."), "unknown"
        )

    def test_hr_domain_message_is_unknown_to_support_agent(self):
        self.assertEqual(
            _support_workflow("Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure."),
            "unknown",
        )
        self.assertEqual(
            _support_workflow("Please onboard John Doe as a Backend Engineer starting next week"),
            "unknown",
        )


if __name__ == "__main__":
    unittest.main()
