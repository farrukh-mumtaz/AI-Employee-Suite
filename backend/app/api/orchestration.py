from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from backend.app.db.database import get_session
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.agent_log import AgentLog
from backend.app.core.graph import build_base_graph
from pydantic import BaseModel

router = APIRouter(prefix="/orchestrate", tags=["orchestration"])

class OrchestrationRequest(BaseModel):
    agent_name: str  # which agent to route to: "hr", "sales", "support", "marketing"
    user_input: str
    system_prompt: str = None

# This maps agent names to their graph-building functions.
# For now all agents use the shared base scaffold; specific agents (HR, Sales, etc.)
# can register their own graph builder here once their custom graphs are ready.
AGENT_REGISTRY = {
    "hr": build_base_graph,
    "sales": build_base_graph,
    "support": build_base_graph,
    "marketing": build_base_graph,
}

# This is the central orchestration endpoint: it receives a request, figures out
# which agent should handle it, runs that agent's graph, and logs the interaction.
@router.post("/")
def route_to_agent(
    data: OrchestrationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if data.agent_name not in AGENT_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {data.agent_name}")

    graph_builder = AGENT_REGISTRY[data.agent_name]
    graph = graph_builder()

    result = graph.invoke({
        "messages": [],
        "user_input": data.user_input,
        "agent_response": None,
        "agent_name": data.agent_name,
        "system_prompt": data.system_prompt,
    })

    # Log this interaction so it shows up in dashboard metrics later
    log_entry = AgentLog(
        agent_name=data.agent_name,
        user_input=data.user_input,
        agent_response=result["agent_response"]
    )
    session.add(log_entry)
    session.commit()

    return {"agent_name": data.agent_name, "response": result["agent_response"]}