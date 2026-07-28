"""
Unit tests for the HR Agent graph's conditional-edge selector functions
(backend/app/agents/hr_agent/graph.py), exercised directly rather than
through a full graph invocation. Full-branch coverage (that routing
actually reaches the right node) is provided by the end-to-end tests in
test_hr_agent.py; these tests pin down the selector functions' own
decision logic in isolation, including defensive fallback behavior that's
hard to trigger through the compiled graph.

Run with: python -m unittest test_hr_agent_graph.py -v
"""
import unittest

from backend.app.agents.hr_agent.graph import _route_by_leave_decision, _route_by_workflow


class RouteByWorkflowTests(unittest.TestCase):
    def test_routes_onboarding(self):
        self.assertEqual(_route_by_workflow({"workflow": "onboarding"}), "onboarding")

    def test_routes_leave_request(self):
        self.assertEqual(_route_by_workflow({"workflow": "leave_request"}), "leave_request")

    def test_defaults_to_unknown_when_workflow_missing(self):
        self.assertEqual(_route_by_workflow({}), "unknown")


class RouteByLeaveDecisionTests(unittest.TestCase):
    def test_routes_approved(self):
        self.assertEqual(_route_by_leave_decision({"leave_decision": "approved"}), "approved")

    def test_routes_rejected(self):
        self.assertEqual(_route_by_leave_decision({"leave_decision": "rejected"}), "rejected")

    def test_defaults_to_rejected_when_decision_missing(self):
        self.assertEqual(_route_by_leave_decision({}), "rejected")

    def test_defaults_to_rejected_for_unrecognized_value(self):
        # Guards against a future change to evaluate_leave_request_node's
        # decision logic dead-ending the graph on an unmapped value.
        self.assertEqual(
            _route_by_leave_decision({"leave_decision": "pending_manual_review"}),
            "rejected",
        )


if __name__ == "__main__":
    unittest.main()
