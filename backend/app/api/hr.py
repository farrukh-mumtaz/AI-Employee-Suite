# HR Agent API router.
#
# Bridges the FastAPI layer to the existing HR Agent LangGraph
# (backend/app/agents/hr_agent/graph.py) without modifying the graph itself.
# The compiled graph is built once at import time -- LangGraph's compiled
# graphs are stateless/reusable across invocations, so there's no need to
# rebuild it per request.
import logging

from fastapi import APIRouter, HTTPException

from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.schemas.hr import HRAgentRequest, HRAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["HR Agent"])

_hr_graph = build_hr_graph()


@router.post("/message", response_model=HRAgentResponse)
def send_hr_message(request: HRAgentRequest) -> HRAgentResponse:
    """Run a single message through the HR Agent graph and return its response.

    Each call is a fresh, independent graph run (no conversation state is
    persisted between requests) -- matching how the graph is exercised in
    the existing test suite (test_hr_agent.py et al.).
    """
    initial_state = {
        "messages": [],
        "user_input": request.user_input,
        "agent_response": None,
        "agent_name": "hr_agent",
    }

    try:
        final_state = _hr_graph.invoke(initial_state)
    except Exception:
        logger.exception("HR agent graph invocation failed")
        raise HTTPException(status_code=500, detail="HR agent failed to process the request")

    agent_response = final_state.get("agent_response")
    if not agent_response:
        logger.error("HR agent graph returned no agent_response for state: %s", final_state)
        raise HTTPException(status_code=500, detail="HR agent produced no response")

    return HRAgentResponse(
        agent_response=agent_response,
        workflow=final_state.get("workflow", "unknown"),
        employee_name=final_state.get("employee_name"),
        employee_role=final_state.get("employee_role"),
        start_date=final_state.get("start_date"),
        onboarding_checklist=final_state.get("onboarding_checklist"),
        leave_type=final_state.get("leave_type"),
        leave_start_date=final_state.get("leave_start_date"),
        leave_end_date=final_state.get("leave_end_date"),
        leave_reason=final_state.get("leave_reason"),
        leave_decision=final_state.get("leave_decision"),
    )
