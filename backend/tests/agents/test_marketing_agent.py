import pytest
from backend.app.agents.marketing_agent.graph import build_marketing_graph


@pytest.fixture(scope="module")
def marketing_graph():
    return build_marketing_graph()


def _base_state(**overrides) -> dict:
    state = {
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": None, "content_topic": None, "platform": None,
        "generated_content": None, "tone": None,
        "campaign_goal": None, "campaign_ideas": None,
        "calendar_period": None, "content_calendar": None,
        "ab_variant_a": None, "ab_variant_b": None, "ab_rationale": None,
    }
    state.update(overrides)
    return state


def test_content_workflow_generates_content(marketing_graph):
    result = marketing_graph.invoke(_base_state(
        workflow="content", content_topic="new product launch",
        platform="instagram", tone="friendly",
    ))
    assert result["generated_content"] is not None
    assert result["campaign_ideas"] is None
    assert result["content_calendar"] is None
    assert result["ab_variant_a"] is None


def test_campaign_ideas_workflow_generates_three_ideas(marketing_graph):
    result = marketing_graph.invoke(_base_state(
        workflow="campaign_ideas", campaign_goal="increase signups",
        content_topic="new mobile app",
    ))
    assert result["campaign_ideas"] is not None
    assert len(result["campaign_ideas"]) == 3
    assert result["generated_content"] is None


def test_content_calendar_workflow_generates_entries(marketing_graph):
    result = marketing_graph.invoke(_base_state(
        workflow="content_calendar", content_topic="product launch",
        calendar_period="1 week",
    ))
    assert result["content_calendar"] is not None
    assert len(result["content_calendar"]) > 0
    assert result["generated_content"] is None


def test_ab_suggestion_workflow_generates_two_variants(marketing_graph):
    result = marketing_graph.invoke(_base_state(
        workflow="ab_suggestion", content_topic="flash sale",
        platform="email", tone="urgent",
    ))
    assert result["ab_variant_a"] is not None
    assert result["ab_variant_b"] is not None
    assert result["ab_variant_a"] != result["ab_variant_b"]
    assert result["ab_rationale"] is not None


def test_invalid_workflow_falls_back_safely(marketing_graph):
    """Regression test for the crash fixed during graph finalization."""
    result = marketing_graph.invoke(_base_state(
        workflow="campaing_ideas",  # deliberate typo
        content_topic="test",
    ))
    assert result["generated_content"] is not None


def test_missing_workflow_falls_back_to_content(marketing_graph):
    result = marketing_graph.invoke(_base_state(content_topic="test topic"))
    assert result["generated_content"] is not None