# Request/response contracts for the HR Agent API (backend/app/api/hr.py).
#
# Kept separate from the graph's own HRAgentState (agents/hr_agent/state.py):
# the API schema is the stable, external-facing contract, while the state
# TypedDict is free to evolve with the graph's internals.
from typing import List, Optional

from pydantic import BaseModel, Field


class HRAgentRequest(BaseModel):
    """Incoming request body for POST /hr/message."""

    user_input: str = Field(..., min_length=1, description="The employee's message to the HR agent")


class HRAgentResponse(BaseModel):
    """Response body for POST /hr/message.

    Every field beyond `agent_response` and `workflow` is optional because
    only one branch of the HR graph (onboarding or leave request) runs per
    request, so only that branch's fields will be populated.
    """

    agent_response: str
    workflow: str

    # Onboarding workflow fields
    employee_name: Optional[str] = None
    employee_role: Optional[str] = None
    start_date: Optional[str] = None
    onboarding_checklist: Optional[List[str]] = None

    # Leave request workflow fields
    leave_type: Optional[str] = None
    leave_start_date: Optional[str] = None
    leave_end_date: Optional[str] = None
    leave_reason: Optional[str] = None
    leave_decision: Optional[str] = None
