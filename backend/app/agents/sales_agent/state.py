from typing import Optional
from backend.app.core.state import AgentState


class SalesLeadState(AgentState):
    """Extends the shared AgentState with Sales Agent-specific fields."""
    intent: Optional[str]       # "hot" / "warm" / "cold"
    lead_name: Optional[str]
    notified: Optional[bool]