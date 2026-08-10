# Request/response contracts for the Orchestrator API (backend/app/api/orchestrator.py).
#
# The response wraps the existing HRAgentResponse / SupportAgentResponse
# schemas (backend/app/schemas/hr.py, backend/app/schemas/support.py) rather
# than redeclaring their fields, so the two agents' response shapes stay the
# single source of truth.
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.hr import HRAgentResponse
from backend.app.schemas.support import SupportAgentResponse


class OrchestratorRequest(BaseModel):
    """Incoming request body for POST /agent/message."""

    user_input: str = Field(
        ..., min_length=1, description="The user's message; the orchestrator decides whether it goes to the HR or Support agent"
    )


class OrchestratorResponse(BaseModel):
    """Response body for POST /agent/message.

    `agent` names which agent handled the request; exactly one of `hr` /
    `support` is populated, matching that agent's own /hr/message or
    /support/message response shape.
    """

    agent: Literal["hr", "support"]
    hr: Optional[HRAgentResponse] = None
    support: Optional[SupportAgentResponse] = None
