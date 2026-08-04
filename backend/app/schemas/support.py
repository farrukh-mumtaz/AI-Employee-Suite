# Request/response contracts for the Support Agent API
# (backend/app/api/support.py).
#
# Kept separate from the graph's own SupportAgentState
# (agents/support_agent/state.py): the API schema is the stable,
# external-facing contract, while the state TypedDict is free to evolve with
# the graph's internals. Mirrors backend/app/schemas/hr.py.
from typing import Optional

from pydantic import BaseModel, Field


class SupportAgentRequest(BaseModel):
    """Incoming request body for POST /support/message."""

    user_input: str = Field(..., min_length=1, description="The customer's message to the Support agent")


class SupportAgentResponse(BaseModel):
    """Response body for POST /support/message.

    Every field beyond `agent_response`, `workflow`, and the ticket fields
    (always populated -- ticket_intake/ticket_classification run for every
    request, regardless of workflow) is optional because only one workflow
    branch (password reset, order status, or refund request) runs per
    request, so only that branch's fields will be populated.
    """

    agent_response: str
    workflow: str

    # Ticket fields -- always populated (see ticket_intake_node / ticket_classification_node)
    ticket_id: Optional[str] = None
    ticket_status: Optional[str] = None
    ticket_priority: Optional[str] = None
    ticket_category: Optional[str] = None
    ticket_category_confidence: Optional[float] = None

    # Password reset workflow fields
    account_email: Optional[str] = None
    reset_link_sent: Optional[bool] = None

    # Order status workflow fields
    order_id: Optional[str] = None
    order_status: Optional[str] = None

    # Refund request workflow fields
    refund_reason: Optional[str] = None
    refund_decision: Optional[str] = None
