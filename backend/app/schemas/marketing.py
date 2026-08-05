from typing import Optional, List, Dict
from pydantic import BaseModel


class MarketingAgentRequest(BaseModel):
    workflow: str  # "content" / "campaign_ideas" / "content_calendar" / "ab_suggestion"
    content_topic: Optional[str] = None
    platform: Optional[str] = None
    tone: Optional[str] = None
    campaign_goal: Optional[str] = None
    calendar_period: Optional[str] = None


class MarketingAgentResponse(BaseModel):
    generated_content: Optional[str] = None
    campaign_ideas: Optional[List[str]] = None
    content_calendar: Optional[List[Dict]] = None
    ab_variant_a: Optional[str] = None
    ab_variant_b: Optional[str] = None
    ab_rationale: Optional[str] = None