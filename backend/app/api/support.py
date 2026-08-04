# Support Agent API router.
#
# The conversational Support Agent LangGraph endpoint (POST /support/message),
# bridging the FastAPI layer to the existing Support Agent graph
# (backend/app/agents/support_agent/graph.py) without modifying it. The
# compiled graph is built once at import time -- LangGraph's compiled graphs
# are stateless/reusable across invocations, so there's no need to rebuild it
# per request. Mirrors backend/app/api/hr.py's POST /hr/message pattern.
import logging

from fastapi import APIRouter, HTTPException

from backend.app.agents.support_agent.graph import build_support_graph
from backend.app.schemas.support import SupportAgentRequest, SupportAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support", tags=["support"])

_support_graph = build_support_graph()


@router.post("/message", response_model=SupportAgentResponse)
def send_support_message(request: SupportAgentRequest) -> SupportAgentResponse:
    """Run a single message through the Support Agent graph and return its response.

    Each call is a fresh, independent graph run (no conversation state is
    persisted between requests) -- matching how the graph is exercised in
    the existing test suite (test_support_agent_graph.py et al.) and how
    /hr/message handles HR Agent requests.
    """
    initial_state = {
        "messages": [],
        "user_input": request.user_input,
        "agent_response": None,
        "agent_name": "support_agent",
    }

    try:
        final_state = _support_graph.invoke(initial_state)
    except Exception:
        logger.exception("Support agent graph invocation failed")
        raise HTTPException(status_code=500, detail="Support agent failed to process the request")

    agent_response = final_state.get("agent_response")
    if not agent_response:
        logger.error("Support agent graph returned no agent_response for state: %s", final_state)
        raise HTTPException(status_code=500, detail="Support agent produced no response")

    return SupportAgentResponse(
        agent_response=agent_response,
        workflow=final_state.get("workflow", "unknown"),
        ticket_id=final_state.get("ticket_id"),
        ticket_status=final_state.get("ticket_status"),
        ticket_priority=final_state.get("ticket_priority"),
        ticket_category=final_state.get("ticket_category"),
        ticket_category_confidence=final_state.get("ticket_category_confidence"),
        account_email=final_state.get("account_email"),
        reset_link_sent=final_state.get("reset_link_sent"),
        order_id=final_state.get("order_id"),
        order_status=final_state.get("order_status"),
        refund_reason=final_state.get("refund_reason"),
        refund_decision=final_state.get("refund_decision"),
    )
