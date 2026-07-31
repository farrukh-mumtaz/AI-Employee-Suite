from typing import Optional
from backend.app.core.state import AgentState


class SalesLeadState(AgentState):
    """Extends the shared AgentState with Sales Agent-specific fields."""
    intent: Optional[str]       # "hot" / "warm" / "cold"
    lead_name: Optional[str]
    notified: Optional[bool]
    followup_email_subject: Optional[str]
    followup_email_body: Optional[str]
    has_objection: Optional[bool]
    objection_response: Optional[str]