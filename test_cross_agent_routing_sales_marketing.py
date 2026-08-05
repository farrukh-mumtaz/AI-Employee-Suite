# Cross-agent routing tests: Sales Agent and Marketing Agent, tested against
# HR/Support-domain input, and against each other.
#
# Sales and Marketing don't have HR/Support's "unknown" classification
# concept (Sales always classifies hot/warm/cold; Marketing always
# generates something for whichever workflow is requested). So this file
# checks the equivalent property for these two agents: domain-mismatched
# input doesn't crash, doesn't produce nonsense, and doesn't leak
# HR/Support-only fields into Sales/Marketing's state shape (or vice versa).
#
# Uses the real LLM (Groq), not a FakeLLM, unlike test_cross_agent_routing.py -
# Sales/Marketing agents were built and tested against the live model
# throughout, so this keeps consistency with their existing test suites
# (test_sales_agent.py, test_marketing_agent.py).
#
# Run with: python -m pytest test_cross_agent_routing_sales_marketing.py -v
import pytest

from backend.app.agents.sales_agent.graph import build_sales_graph
from backend.app.agents.marketing_agent.graph import build_marketing_graph


_HR_DOMAIN_MESSAGE = "Please onboard John Doe as a Backend Engineer starting next week"
_SUPPORT_DOMAIN_MESSAGE = "I forgot my password and I'm locked out of my account"


@pytest.fixture(scope="module")
def sales_graph():
    return build_sales_graph()


@pytest.fixture(scope="module")
def marketing_graph():
    return build_marketing_graph()


def _sales_state(message):
    return {
        "messages": [], "user_input": message, "agent_response": None,
        "agent_name": "sales_agent",
        "system_prompt": "You are a sales assistant for a company.",
        "intent": None, "lead_name": "Test", "notified": None,
        "followup_email_subject": None, "followup_email_body": None,
        "has_objection": None, "objection_response": None,
    }


def _marketing_state(topic, platform="instagram", tone="friendly"):
    return {
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing_agent",
        "system_prompt": "You are a marketing assistant.",
        "workflow": "content",
        "content_topic": topic, "platform": platform,
        "generated_content": None, "tone": tone,
        "campaign_goal": None, "campaign_ideas": None,
        "calendar_period": None, "content_calendar": None,
        "ab_variant_a": None, "ab_variant_b": None, "ab_rationale": None,
    }


class TestOffDomainInputThroughSalesAgent:
    def test_hr_domain_message_does_not_crash(self, sales_graph):
        result = sales_graph.invoke(_sales_state(_HR_DOMAIN_MESSAGE))
        assert result["agent_response"] is not None
        assert result["intent"] in ("hot", "warm", "cold")
        assert "ticket_id" not in result
        assert "employee_name" not in result
        assert "leave_decision" not in result

    def test_support_domain_message_does_not_crash(self, sales_graph):
        result = sales_graph.invoke(_sales_state(_SUPPORT_DOMAIN_MESSAGE))
        assert result["agent_response"] is not None
        assert result["intent"] in ("hot", "warm", "cold")
        assert "ticket_id" not in result
        assert "onboarding_checklist" not in result


class TestOffDomainInputThroughMarketingAgent:
    def test_hr_style_topic_does_not_crash(self, marketing_graph):
        result = marketing_graph.invoke(_marketing_state("employee onboarding process", "linkedin", "professional"))
        assert result["generated_content"] is not None
        assert "ticket_id" not in result
        assert "intent" not in result
        assert "employee_name" not in result


class TestSalesAndMarketingFieldsDoNotCrossPollinate:
    def test_marketing_result_has_no_sales_fields(self, marketing_graph):
        result = marketing_graph.invoke(_marketing_state("new launch"))
        assert "intent" not in result
        assert "notified" not in result
        assert "has_objection" not in result

    def test_sales_result_has_no_marketing_fields(self, sales_graph):
        result = sales_graph.invoke(_sales_state("Interested in pricing"))
        assert "generated_content" not in result
        assert "campaign_ideas" not in result
        assert "ab_variant_a" not in result
