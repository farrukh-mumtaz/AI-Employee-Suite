import json
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