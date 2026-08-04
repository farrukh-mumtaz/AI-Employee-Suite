from typing import Optional, List, Dict
from backend.app.core.state import AgentState


class MarketingContentState(AgentState):
    """Extends the shared AgentState with Marketing Agent-specific fields."""
    workflow: Optional[str]           # "content" / "campaign_ideas" / "content_calendar"
    content_topic: Optional[str]
    platform: Optional[str]
    generated_content: Optional[str]
    tone: Optional[str]
    campaign_goal: Optional[str]
    campaign_ideas: Optional[List[str]]
    calendar_period: Optional[str]        # e.g. "1 week", "5 days"
    content_calendar: Optional[List[Dict]]  # list of {day, platform, idea}