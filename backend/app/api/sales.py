# Sales Agent API router.
#
# Bridges the FastAPI layer to the existing Sales Agent LangGraph
# (backend/app/agents/sales_agent/graph.py) without modifying it, matching
# the same pattern used by backend/app/api/hr.py. The compiled graph is
# built once at import time since LangGraph's compiled graphs are
# stateless/reusable across invocations.
import logging

from fastapi import APIRouter, HTTPException

from backend.app.agents.sales_agent.graph import build_sales_graph
from backend.app.schemas.sales import SalesAgentRequest, SalesAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["sales"])

_sales_graph = build_sales_graph()


@router.post("/message", response_model=SalesAgentResponse)
def send_sales_message(request: SalesAgentRequest) -> SalesAgentResponse:
    """Run a single lead message through the Sales Agent graph and return its response.

    Each call is a fresh, independent graph run (no conversation state is
    persisted between requests) -- matching how the graph is exercised in
    the existing test suite (test_sales_agent.py).
    """
    initial_state = {
        "messages": [],
        "user_input": request.user_input,
        "agent_response": None,
        "agent_name": "sales_agent",
        "system_prompt": "You are a sales assistant for a company.",
        "intent": None,
        "lead_name": request.lead_name,
        "notified": None,
        "followup_email_subject": None,
        "followup_email_body": None,
        "has_objection": None,
        "objection_response": None,
    }

    try:
        final_state = _sales_graph.invoke(initial_state)
    except Exception:
        logger.exception("Sales agent graph invocation failed")
        raise HTTPException(status_code=500, detail="Sales agent failed to process the request")

    agent_response = final_state.get("agent_response")
    if not agent_response:
        logger.error("Sales agent graph returned no agent_response for state: %s", final_state)
        raise HTTPException(status_code=500, detail="Sales agent produced no response")

    return SalesAgentResponse(
        agent_response=agent_response,
        intent=final_state.get("intent"),
        notified=final_state.get("notified"),
        followup_email_subject=final_state.get("followup_email_subject"),
        followup_email_body=final_state.get("followup_email_body"),
        has_objection=final_state.get("has_objection"),
        objection_response=final_state.get("objection_response"),
    )