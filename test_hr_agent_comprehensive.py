"""
Comprehensive HR Agent test suite.

Complements the existing HR Agent tests rather than duplicating them:
    - test_hr_agent.py            -- end-to-end happy-path workflows
    - test_hr_agent_nodes.py      -- individual node unit tests
    - test_hr_agent_graph.py      -- conditional-edge selector unit tests
    - test_hr_agent_extraction.py -- extraction.py heuristics

This file adds the gaps: explicit graph-compilation checks, rag.py unit
tests (previously untested in isolation), invalid/missing/empty/unicode
input handling at the full-graph level, additional realistic multi-field
onboarding and leave scenarios, and state-isolation across repeated
invocations of the same compiled graph.

Follows the same conventions as the rest of the suite: unittest.TestCase,
a self-contained FakeLLM/FakeResponse stand-in for ChatGroq (patched onto
`backend.app.agents.hr_agent.nodes.get_llm`), and a shared `_initial_state`
helper -- no HR Agent source files are modified.

Run with: python -m unittest test_hr_agent_comprehensive.py -v
"""
import unittest
from unittest.mock import patch

from backend.app.agents.hr_agent import nodes as hr_nodes
from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.agents.hr_agent.rag import retrieve_leave_policy


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Deterministic stand-in for ChatGroq, mirroring the FakeLLM used in
    test_hr_agent.py so both files' end-to-end behavior stays consistent."""

    def invoke(self, prompt: str) -> FakeResponse:
        lowered = prompt.lower()

        if "intent classifier" in lowered:
            user_message = lowered.rsplit("user message:", 1)[-1]
            if "onboard" in user_message or "new hire" in user_message or "employee" in user_message:
                return FakeResponse("onboarding")
            if "leave" in user_message or "vacation" in user_message or "sick" in user_message or "pto" in user_message:
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


def _initial_state(user_input) -> dict:
    return {
        "messages": [],
        "user_input": user_input,
        "agent_response": None,
        "agent_name": "hr_agent",
    }


class GraphCompilationTests(unittest.TestCase):
    """Graph construction/compilation should be deterministic, cheap to
    repeat, and expose the node wiring described in graph.py's docstring."""

    def test_build_hr_graph_compiles_without_error(self):
        graph = build_hr_graph()
        self.assertIsNotNone(graph)

    def test_build_hr_graph_is_repeatable_and_independent(self):
        # Building twice must not raise (e.g. from re-registering nodes on a
        # shared graph object) and must yield two independent instances.
        first = build_hr_graph()
        second = build_hr_graph()
        self.assertIsNot(first, second)

    def test_compiled_graph_contains_all_expected_nodes(self):
        graph = build_hr_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "classify_intent",
            "extract_employee_details",
            "generate_welcome_message",
            "generate_onboarding_checklist",
            "extract_leave_details",
            "retrieve_leave_policy",
            "evaluate_leave_request",
            "approve_leave",
            "reject_leave",
            "unknown_intent",
        }
        self.assertTrue(expected.issubset(node_names))


class RetrieveLeavePolicyTests(unittest.TestCase):
    """Direct unit tests for rag.py, which had no dedicated coverage
    elsewhere in the suite."""

    def test_empty_query_returns_top_k_general_docs(self):
        docs = retrieve_leave_policy("", top_k=3)
        self.assertEqual(len(docs), 3)

    def test_keyword_match_surfaces_relevant_doc(self):
        docs = retrieve_leave_policy("sick")
        self.assertTrue(any("sick" in doc.lower() for doc in docs))

    def test_no_keyword_overlap_falls_back_to_general_docs(self):
        # No word in the query shares a substring with any policy doc, so
        # retrieval must fall back to the general set rather than returning
        # an empty list.
        docs = retrieve_leave_policy("xylophone")
        self.assertGreater(len(docs), 0)

    def test_top_k_is_respected(self):
        docs = retrieve_leave_policy("leave days notice manager", top_k=1)
        self.assertEqual(len(docs), 1)


class GraphInvalidAndEmptyInputTests(unittest.TestCase):
    """Full-graph behavior for missing, empty, malformed, or unusual input
    -- the graph must never raise, and must fall back to the unknown-intent
    branch when there's nothing usable to classify."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_missing_user_input_key_does_not_raise(self):
        state = {"messages": [], "agent_response": None, "agent_name": "hr_agent"}
        result = self.graph.invoke(state)
        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_none_user_input_does_not_raise(self):
        result = self.graph.invoke(_initial_state(None))
        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_empty_string_input_routes_to_unknown(self):
        result = self.graph.invoke(_initial_state(""))
        self.assertEqual(result["workflow"], "unknown")

    def test_whitespace_only_input_routes_to_unknown(self):
        result = self.graph.invoke(_initial_state("   \n\t  "))
        self.assertEqual(result["workflow"], "unknown")

    def test_numeric_only_input_does_not_raise(self):
        result = self.graph.invoke(_initial_state("123456789"))
        self.assertEqual(result["workflow"], "unknown")
        self.assertIsNotNone(result["agent_response"])

    def test_unicode_and_emoji_input_does_not_raise(self):
        result = self.graph.invoke(
            _initial_state("新しい従業員のオンボーディングをお願いします 🎉 new hire onboarding")
        )
        self.assertEqual(result["workflow"], "onboarding")
        self.assertIsNotNone(result["agent_response"])

    def test_very_long_input_does_not_raise(self):
        long_input = "I need sick leave from Aug 1 to Aug 3. " * 500
        result = self.graph.invoke(_initial_state(long_input))
        self.assertEqual(result["workflow"], "leave_request")
        self.assertIsNotNone(result["agent_response"])


class OnboardingRealisticScenarioTests(unittest.TestCase):
    """Additional realistic onboarding phrasings beyond the single scenario
    covered in test_hr_agent.py, exercising extraction + welcome message +
    checklist together through the compiled graph."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_full_details_are_extracted_and_checklist_attached(self):
        result = self.graph.invoke(
            _initial_state(
                "Please onboard our new hire, Maria Alvarez, who starts as a "
                "Senior Data Analyst on 2026-09-15."
            )
        )
        self.assertEqual(result["workflow"], "onboarding")
        self.assertEqual(result["employee_name"], "Maria Alvarez")
        self.assertEqual(result["employee_role"], "Senior Data Analyst")
        self.assertEqual(result["start_date"], "2026-09-15")
        self.assertIsInstance(result["onboarding_checklist"], list)
        self.assertGreater(len(result["onboarding_checklist"]), 0)
        self.assertIsNotNone(result["agent_response"])

    def test_partial_details_fall_back_to_unknown_placeholders(self):
        # No name/role marker phrases and no article before the job title,
        # so extraction can't confidently pull employee_name/role -- the
        # workflow should still complete gracefully with "Unknown" fallbacks
        # rather than failing.
        result = self.graph.invoke(
            _initial_state("Employee John starts Junior DevOps Engineer on 2026-09-01.")
        )
        self.assertEqual(result["workflow"], "onboarding")
        self.assertEqual(result["employee_role"], "Unknown")
        self.assertEqual(result["start_date"], "2026-09-01")
        self.assertIsNotNone(result["agent_response"])

    def test_preexisting_employee_fields_are_not_overwritten_end_to_end(self):
        state = _initial_state("New hire onboarding request, please start the process.")
        state["employee_name"] = "Provided Name"
        state["employee_role"] = "Provided Role"
        state["start_date"] = "2026-01-01"

        result = self.graph.invoke(state)

        self.assertEqual(result["workflow"], "onboarding")
        self.assertEqual(result["employee_name"], "Provided Name")
        self.assertEqual(result["employee_role"], "Provided Role")
        self.assertEqual(result["start_date"], "2026-01-01")


class LeaveRequestRealisticScenarioTests(unittest.TestCase):
    """Additional leave-request phrasings/leave types and partial-detail
    combinations beyond the two scenarios in test_hr_agent.py."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_maternity_leave_with_full_details_is_approved(self):
        result = self.graph.invoke(
            _initial_state(
                "I would like to request maternity leave from 2026-10-01 to 2026-12-01."
            )
        )
        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "maternity leave")
        self.assertEqual(result["leave_decision"], "approved")

    def test_unpaid_leave_single_day_uses_same_start_and_end_date(self):
        result = self.graph.invoke(
            _initial_state("Requesting unpaid leave on 2026-11-05 for personal reasons.")
        )
        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "unpaid leave")
        self.assertEqual(result["leave_start_date"], "2026-11-05")
        self.assertEqual(result["leave_end_date"], "2026-11-05")
        self.assertEqual(result["leave_decision"], "approved")

    def test_known_type_but_missing_dates_is_rejected_for_manual_review(self):
        result = self.graph.invoke(
            _initial_state("I need to take vacation but I'm not sure of the dates yet.")
        )
        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "vacation")
        self.assertEqual(result["leave_start_date"], "Unspecified")
        self.assertEqual(result["leave_decision"], "rejected")

    def test_known_dates_but_unrecognized_type_is_rejected_for_manual_review(self):
        result = self.graph.invoke(
            _initial_state("I need to request leave from 2026-08-01 to 2026-08-05, not sure what kind.")
        )
        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "Unspecified")
        self.assertEqual(result["leave_decision"], "rejected")

    def test_preexisting_leave_fields_are_not_overwritten_end_to_end(self):
        state = _initial_state("I need to request leave, please process it.")
        state["leave_type"] = "sick leave"
        state["leave_start_date"] = "2026-01-01"
        state["leave_end_date"] = "2026-01-02"

        result = self.graph.invoke(state)

        self.assertEqual(result["workflow"], "leave_request")
        self.assertEqual(result["leave_type"], "sick leave")
        self.assertEqual(result["leave_start_date"], "2026-01-01")
        self.assertEqual(result["leave_end_date"], "2026-01-02")
        self.assertEqual(result["leave_decision"], "approved")


class StateIsolationTests(unittest.TestCase):
    """A single compiled graph instance is reused across multiple invoke()
    calls in production (e.g. one process serving many requests) -- state
    from one invocation must never leak into the next."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_onboarding_then_leave_request_do_not_leak_state(self):
        onboarding_result = self.graph.invoke(
            _initial_state("New hire, Jane Smith, starts as a Product Manager next Monday.")
        )
        self.assertEqual(onboarding_result["workflow"], "onboarding")

        leave_result = self.graph.invoke(
            _initial_state("I need to request sick leave from Aug 1 to Aug 3.")
        )
        self.assertEqual(leave_result["workflow"], "leave_request")
        # Fields set by the previous (onboarding) invocation must not
        # reappear in this unrelated leave-request result.
        self.assertIsNone(leave_result.get("employee_name"))
        self.assertIsNone(leave_result.get("onboarding_checklist"))

    def test_onboarding_checklist_template_is_not_mutated_across_invocations(self):
        from backend.app.agents.hr_agent import prompts

        original_length = len(prompts.ONBOARDING_CHECKLIST_TEMPLATE)

        first = self.graph.invoke(_initial_state("Onboard our new hire starting next week."))
        first["onboarding_checklist"].append("mutated by test")

        second = self.graph.invoke(_initial_state("Onboard another new hire starting next week."))

        self.assertEqual(len(prompts.ONBOARDING_CHECKLIST_TEMPLATE), original_length)
        self.assertNotIn("mutated by test", second["onboarding_checklist"])

    def test_repeated_invocations_produce_distinct_result_dicts(self):
        first = self.graph.invoke(_initial_state("Onboard our new hire starting next week."))
        second = self.graph.invoke(_initial_state("Onboard our new hire starting next week."))
        self.assertIsNot(first, second)
        self.assertIsNot(first["onboarding_checklist"], second["onboarding_checklist"])


class FinalStateShapeTests(unittest.TestCase):
    """Sanity checks on the overall shape of the final state dict returned
    by graph.invoke(), independent of which branch ran."""

    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.graph = build_hr_graph()

    def test_base_agent_state_fields_survive_every_branch(self):
        for user_input in (
            "Onboard our new hire starting next week.",
            "I need sick leave from Aug 1 to Aug 3.",
            "What's the weather like today?",
        ):
            with self.subTest(user_input=user_input):
                result = self.graph.invoke(_initial_state(user_input))
                self.assertEqual(result["user_input"], user_input)
                self.assertEqual(result["agent_name"], "hr_agent")
                self.assertEqual(result["messages"], [])
                self.assertIn("agent_response", result)
                self.assertIn("workflow", result)


if __name__ == "__main__":
    unittest.main()
