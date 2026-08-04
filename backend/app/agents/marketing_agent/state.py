from typing import Optional, List, Dict
from backend.app.core.state import AgentState


class MarketingContentState(AgentState):
    """Extends the shared AgentState with Marketing Agent-specific fields."""
    workflow: Optional[str]           # "content" / "campaign_ideas" / "content_calendar" / "ab_suggestion"
    content_topic: Optional[str]
    platform: Optional[str]
    generated_content: Optional[str]
    tone: Optional[str]
    campaign_goal: Optional[str]
    campaign_ideas: Optional[List[str]]
    calendar_period: Optional[str]
    content_calendar: Optional[List[Dict]]
    ab_variant_a: Optional[str]
    ab_variant_b: Optional[str]
    ab_rationale: Optional[str]