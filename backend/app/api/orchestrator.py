# Orchestrator API router.
#
# Single entry point (POST /agent/message) that routes an incoming message to
# whichever of the existing HR Agent or Support Agent graphs should handle it
# (backend/app/core/orchestrator.py), for callers that don't know in advance
# which agent a message belongs to. Bridges to the orchestrator graph without
# modifying either agent's graph, nodes, or state. The compiled graph is
# built once at import time -- LangGraph's compiled graphs are
# stateless/reusable across invocations. Mirrors backend/app/api/hr.py and
# backend/app/api/support.py's "build once, invoke per request" pattern.
import logging

from fastapi import APIRouter, HTTPException

from backend.app.core.orchestrator import build_orchestrator_graph
from backend.app.schemas.hr import HRAgentResponse
from backend.app.schemas.orchestrator import OrchestratorRequest, OrchestratorResponse
from backend.app.schemas.support import SupportAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["orchestrator"])

_orchestrator_graph = build_orchestrator_graph()


@router.post("/message", response_model=OrchestratorResponse)
def send_agent_message(request: OrchestratorRequest) -> OrchestratorResponse:
    """Route a single message to the HR or Support agent and return its response.

    Each call is a fresh, independent run (no conversation state persisted
    between requests) -- matching /hr/message and /support/message.
    """
    initial_state = {
        "messages": [],
        "user_input": request.user_input,
        "agent_response": None,
        "agent_name": "orchestrator",
    }

    try:
        final_state = _orchestrator_graph.invoke(initial_state)
    except Exception:
        logger.exception("Orchestrator graph invocation failed")
        raise HTTPException(status_code=500, detail="Orchestrator failed to process the request")

    target_agent = final_state.get("target_agent")

    if target_agent == "hr":
        hr_state = final_state.get("hr_result") or {}
        agent_response = hr_state.get("agent_response")
        if not agent_response:
            logger.error("HR agent produced no response for state: %s", hr_state)
            raise HTTPException(status_code=500, detail="HR agent produced no response")
        return OrchestratorResponse(
            agent="hr",
            hr=HRAgentResponse(
                agent_response=agent_response,
                workflow=hr_state.get("workflow", "unknown"),
                employee_name=hr_state.get("employee_name"),
                employee_role=hr_state.get("employee_role"),
                start_date=hr_state.get("start_date"),
                onboarding_checklist=hr_state.get("onboarding_checklist"),
                leave_type=hr_state.get("leave_type"),
                leave_start_date=hr_state.get("leave_start_date"),
                leave_end_date=hr_state.get("leave_end_date"),
                leave_reason=hr_state.get("leave_reason"),
                leave_decision=hr_state.get("leave_decision"),
            ),
        )

    support_state = final_state.get("support_result") or {}
    agent_response = support_state.get("agent_response")
    if not agent_response:
        logger.error("Support agent produced no response for state: %s", support_state)
        raise HTTPException(status_code=500, detail="Support agent produced no response")
    return OrchestratorResponse(
        agent="support",
        support=SupportAgentResponse(
            agent_response=agent_response,
            workflow=support_state.get("workflow", "unknown"),
            ticket_id=support_state.get("ticket_id"),
            ticket_status=support_state.get("ticket_status"),
            ticket_priority=support_state.get("ticket_priority"),
            ticket_category=support_state.get("ticket_category"),
            ticket_category_confidence=support_state.get("ticket_category_confidence"),
            account_email=support_state.get("account_email"),
            reset_link_sent=support_state.get("reset_link_sent"),
            order_id=support_state.get("order_id"),
            order_status=support_state.get("order_status"),
            refund_reason=support_state.get("refund_reason"),
            refund_decision=support_state.get("refund_decision"),
        ),
    )
