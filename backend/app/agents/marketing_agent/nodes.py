import json
from backend.app.agents.marketing_agent.prompts import (
    CONTENT_GENERATION_PROMPT,
    CAMPAIGN_IDEA_PROMPT,
    CONTENT_CALENDAR_PROMPT,
)
from backend.app.agents.marketing_agent.prompts import (
    CONTENT_GENERATION_PROMPT,
    CAMPAIGN_IDEA_PROMPT,
)
from backend.app.core.llm_client import get_llm
from backend.app.agents.marketing_agent.state import MarketingContentState
from backend.app.agents.marketing_agent.prompts import CONTENT_GENERATION_PROMPT


def generate_content_node(state: MarketingContentState) -> MarketingContentState:
    """Generates marketing content based on topic, platform, and tone."""
    llm = get_llm()

    prompt = CONTENT_GENERATION_PROMPT.format(
        system_prompt=state.get("system_prompt") or "You are a marketing assistant.",
        content_topic=state.get("content_topic", "our product"),
        platform=state.get("platform", "social media"),
        tone=state.get("tone", "friendly"),
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["generated_content"] = result["content"]
    return state

def generate_campaign_ideas_node(state: MarketingContentState) -> MarketingContentState:
    """Brainstorms 3 distinct marketing campaign concepts for a given goal."""
    llm = get_llm()

    prompt = CAMPAIGN_IDEA_PROMPT.format(
        system_prompt=state.get("system_prompt") or "You are a marketing assistant.",
        campaign_goal=state.get("campaign_goal", "increase engagement"),
        content_topic=state.get("content_topic", "our product"),
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["campaign_ideas"] = result["ideas"]
    return state

def generate_content_calendar_node(state: MarketingContentState) -> MarketingContentState:
    """Generates a spread of dated content ideas across a given time period."""
    llm = get_llm()

    prompt = CONTENT_CALENDAR_PROMPT.format(
        system_prompt=state.get("system_prompt") or "You are a marketing assistant.",
        content_topic=state.get("content_topic", "our product"),
        calendar_period=state.get("calendar_period", "1 week"),
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["content_calendar"] = result["calendar"]
    return state