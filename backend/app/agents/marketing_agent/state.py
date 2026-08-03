from typing import Optional, List
from backend.app.core.state import AgentState


class MarketingContentState(AgentState):
    """Extends the shared AgentState with Marketing Agent-specific fields."""
    workflow: Optional[str]           # "content" or "campaign_ideas"
    content_topic: Optional[str]
    platform: Optional[str]
    generated_content: Optional[str]
    tone: Optional[str]
    campaign_goal: Optional[str]
    campaign_ideas: Optional[List[str]]