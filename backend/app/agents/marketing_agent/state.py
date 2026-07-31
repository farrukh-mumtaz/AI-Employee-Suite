from typing import Optional
from backend.app.core.state import AgentState


class MarketingContentState(AgentState):
    """Extends the shared AgentState with Marketing Agent-specific fields."""
    content_topic: Optional[str]      # what the content should be about
    platform: Optional[str]           # e.g. "instagram", "linkedin", "email"
    generated_content: Optional[str]  # the AI-generated post/caption/copy
    tone: Optional[str]               # e.g. "friendly", "professional"