from backend.app.core.llm_client import get_llm
from backend.app.agents.marketing_agent.state import MarketingContentState
from backend.app.agents.marketing_agent.prompts import CONTENT_GENERATION_PROMPT


def generate_content_node(state: MarketingContentState) -> MarketingContentState:
    """Placeholder scaffold node - full content-generation logic to follow."""
    state["generated_content"] = "TODO: implement content generation"
    return state