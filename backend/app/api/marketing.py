# Marketing Agent API router.
#
# Bridges the FastAPI layer to the existing Marketing Agent LangGraph
# (backend/app/agents/marketing_agent/graph.py) without modifying it,
# matching the same pattern used by backend/app/api/hr.py and
# backend/app/api/sales.py. The compiled graph is built once at import
# time since LangGraph's compiled graphs are stateless/reusable across
# invocations.
#
# Unlike HR/Support/Sales, Marketing has no single "message" - the caller
# picks a workflow (content / campaign_ideas / content_calendar /
# ab_suggestion) directly, matching how the graph is exercised in the
# existing test suite (test_marketing_agent.py).
import logging

from fastapi import APIRouter, HTTPException

from backend.app.agents.marketing_agent.graph import build_marketing_graph
from backend.app.schemas.marketing import MarketingAgentRequest, MarketingAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketing", tags=["marketing"])

_marketing_graph = build_marketing_graph()


@router.post("/generate", response_model=MarketingAgentResponse)
def generate_marketing_content(request: MarketingAgentRequest) -> MarketingAgentResponse:
    """Run a single request through the Marketing Agent graph and return its response.

    The graph's own routing falls back safely to "content" generation for
    any invalid/missing workflow value (see graph.py's _route_by_workflow),
    so this endpoint never needs to validate `workflow` itself.
    """
    initial_state = {
        "messages": [],
        "user_input": None,
        "agent_response": None,
        "agent_name": "marketing_agent",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": request.workflow,
        "content_topic": request.content_topic,
        "platform": request.platform,
        "generated_content": None,
        "tone": request.tone,
        "campaign_goal": request.campaign_goal,
        "campaign_ideas": None,
        "calendar_period": request.calendar_period,
        "content_calendar": None,
        "ab_variant_a": None,
        "ab_variant_b": None,
        "ab_rationale": None,
    }

    try:
        final_state = _marketing_graph.invoke(initial_state)
    except Exception:
        logger.exception("Marketing agent graph invocation failed")
        raise HTTPException(status_code=500, detail="Marketing agent failed to process the request")

    return MarketingAgentResponse(
        generated_content=final_state.get("generated_content"),
        campaign_ideas=final_state.get("campaign_ideas"),
        content_calendar=final_state.get("content_calendar"),
        ab_variant_a=final_state.get("ab_variant_a"),
        ab_variant_b=final_state.get("ab_variant_b"),
        ab_rationale=final_state.get("ab_rationale"),
    )