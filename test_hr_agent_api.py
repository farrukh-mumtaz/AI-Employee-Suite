# API-layer tests for the HR Agent FastAPI endpoint
# (backend/app/api/hr.py -- POST /hr/message).
#
# No prior test file covered this layer: test_hr_agent.py, test_hr_agent_nodes.py,
# test_hr_agent_graph.py, test_hr_agent_extraction.py, and
# test_hr_agent_comprehensive.py all exercise the graph/nodes/extraction/rag
# directly, never through FastAPI. This file complements them by covering
# request validation, response shape, and the endpoint's own error handling
# (a failing graph invocation, an empty agent_response) -- concerns that only
# exist at the HTTP boundary.
#
# Uses FastAPI's TestClient (starlette test client) against the real `app`
# from backend/app/main.py, with the LLM stubbed the same way as the rest of
# the suite (patch.object on `backend.app.agents.hr_agent.nodes.get_llm`) so
# it runs deterministically with no network access / GROQ_API_KEY needed.
#
# Run with: python -m pytest test_hr_agent_api.py -v
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.agents.hr_agent import nodes as hr_nodes
from backend.app.api import hr as hr_api
from backend.app.main import app


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """Same deterministic stand-in used by test_hr_agent.py and
    test_hr_agent_comprehensive.py, kept in sync so all three files agree on
    what each canned prompt should return."""

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
            return FakeResponse("Welcome aboard! We're excited to have you join us.")

        if "confirming an approved leave request" in lowered:
            return FakeResponse("Your leave request has been approved. Enjoy your time off!")

        if "responding to a leave request that could not be" in lowered:
            return FakeResponse(
                "We couldn't automatically process your leave request; it has "
                "been forwarded to HR for manual review."
            )

        raise AssertionError(f"FakeLLM received an unexpected prompt: {prompt!r}")


class HRMessageEndpointHappyPathTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(hr_nodes, "get_llm", return_value=FakeLLM())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)

    def test_onboarding_request_returns_200_with_expected_fields(self):
        response = self.client.post(
            "/hr/message",
            json={
                "user_input": (
                    "New hire, Jane Smith, joining as a Product Manager "
                    "starting 2026-08-15."
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "onboarding")
        self.assertEqual(body["employee_name"], "Jane Smith")
        self.assertEqual(body["employee_role"], "Product Manager")
        self.assertEqual(body["start_date"], "2026-08-15")
        self.assertIsInstance(body["onboarding_checklist"], list)
        self.assertGreater(len(body["onboarding_checklist"]), 0)
        self.assertTrue(body["agent_response"])

    def test_leave_request_with_full_details_is_approved(self):
        response = self.client.post(
            "/hr/message",
            json={
                "user_input": (
                    "Requesting sick leave from Aug 1 to Aug 3 because of a "
                    "medical procedure."
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "leave_request")
        self.assertEqual(body["leave_type"], "sick leave")
        self.assertEqual(body["leave_reason"], "a medical procedure")
        self.assertEqual(body["leave_decision"], "approved")

    def test_leave_request_with_missing_details_is_routed_to_manual_review(self):
        response = self.client.post(
            "/hr/message",
            json={"user_input": "I need to request leave, not sure of the dates yet."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "leave_request")
        self.assertEqual(body["leave_decision"], "rejected")

    def test_unrecognized_input_falls_back_to_unknown(self):
        response = self.client.post("/hr/message", json={"user_input": "What's the weather like?"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["workflow"], "unknown")
        self.assertTrue(body["agent_response"])


class HRMessageEndpointInvalidInputTests(unittest.TestCase):
    """No LLM patching needed here -- these requests are rejected by Pydantic
    validation before the graph ever runs."""

    def setUp(self):
        self.client = TestClient(app)

    def test_empty_user_input_returns_422(self):
        response = self.client.post("/hr/message", json={"user_input": ""})
        self.assertEqual(response.status_code, 422)

    def test_missing_user_input_field_returns_422(self):
        response = self.client.post("/hr/message", json={})
        self.assertEqual(response.status_code, 422)

    def test_wrong_type_for_user_input_returns_422(self):
        response = self.client.post("/hr/message", json={"user_input": 12345})
        self.assertEqual(response.status_code, 422)

    def test_non_json_body_returns_422(self):
        response = self.client.post(
            "/hr/message",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422)


class HRMessageEndpointErrorHandlingTests(unittest.TestCase):
    """The endpoint must translate internal failures into a clean 500 rather
    than leaking a raw traceback/500 with no detail."""

    def setUp(self):
        self.client = TestClient(app)

    def test_graph_invocation_failure_returns_500_with_detail(self):
        with patch.object(hr_api._hr_graph, "invoke", side_effect=RuntimeError("boom")):
            response = self.client.post("/hr/message", json={"user_input": "Onboard our new hire."})
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())

    def test_empty_agent_response_returns_500_with_detail(self):
        with patch.object(
            hr_api._hr_graph,
            "invoke",
            return_value={"workflow": "unknown", "agent_response": None},
        ):
            response = self.client.post("/hr/message", json={"user_input": "Onboard our new hire."})
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
