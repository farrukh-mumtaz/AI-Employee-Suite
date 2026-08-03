import pytest
from backend.app.agents.sales_agent.graph import build_sales_graph


@pytest.fixture(scope="module")
def sales_graph():
    """Build the compiled graph once and reuse it across all tests in this file."""
    return build_sales_graph()


def _base_state(name: str, message: str) -> dict:
    return {
        "messages": [],
        "user_input": message,
        "agent_response": None,
        "agent_name": "sales",
        "system_prompt": "You are a sales assistant for a company.",
        "intent": None,
        "lead_name": name,
        "notified": None,
        "followup_email_subject": None,
        "followup_email_body": None,
        "has_objection": None,
        "objection_response": None,
    }


def test_hot_lead_gets_notified_and_followup_email(sales_graph):
    """A clearly hot lead should be classified as hot, notified, and get a follow-up email."""
    result = sales_graph.invoke(
        _base_state("Ali", "We want to sign up this week, please send pricing for the enterprise plan")
    )

    assert result["intent"] == "hot"
    assert result["notified"] is True
    assert result["followup_email_subject"] is not None
    assert result["followup_email_body"] is not None
    assert "[HOT LEAD" in result["agent_response"]


def test_cold_lead_is_not_notified_and_gets_no_email(sales_graph):
    """A clearly cold lead should not be notified and should not get a follow-up email."""
    result = sales_graph.invoke(
        _base_state("Sara", "Just browsing, not looking to buy anything right now")
    )

    assert result["intent"] in ("cold", "warm")
    assert result["notified"] is False
    assert result["followup_email_subject"] is None
    assert result["followup_email_body"] is None


def test_vague_message_does_not_crash(sales_graph):
    """A one-word vague message should still produce a valid result, not an error."""
    result = sales_graph.invoke(_base_state("Zain", "hey"))

    assert result["intent"] in ("hot", "warm", "cold")
    assert result["agent_response"] is not None


def test_empty_message_does_not_crash(sales_graph):
    """An empty message should be handled gracefully, not raise an exception."""
    result = sales_graph.invoke(_base_state("Hina", ""))

    assert result["intent"] in ("hot", "warm", "cold")
    assert result["agent_response"] is not None


def test_only_hot_leads_get_followup_email(sales_graph):
    """Structural check: followup fields should only be populated when notified is True."""
    result = sales_graph.invoke(
        _base_state("Bilal", "Might be interested down the line, tell me more")
    )

    if result["notified"] is True:
        assert result["followup_email_subject"] is not None
    else:
        assert result["followup_email_subject"] is None
        assert result["followup_email_body"] is None


def test_objection_is_detected_and_reflected_in_state(sales_graph):
    """A message with a clear price objection should be flagged as an objection."""
    result = sales_graph.invoke(
        _base_state("Noor", "This seems way too expensive compared to competitors")
    )

    assert result["has_objection"] is True
    assert result["objection_response"] != ""