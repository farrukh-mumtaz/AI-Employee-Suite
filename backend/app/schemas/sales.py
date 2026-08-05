from typing import Optional
from pydantic import BaseModel


class SalesAgentRequest(BaseModel):
    user_input: str
    lead_name: Optional[str] = None


class SalesAgentResponse(BaseModel):
    agent_response: Optional[str] = None
    intent: Optional[str] = None
    notified: Optional[bool] = None
    followup_email_subject: Optional[str] = None
    followup_email_body: Optional[str] = None
    has_objection: Optional[bool] = None
    objection_response: Optional[str] = None