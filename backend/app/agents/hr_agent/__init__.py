"""HR Agent: onboarding and leave-request workflows built on the shared
LangGraph scaffold (backend/app/core)."""
from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.agents.hr_agent.state import HRAgentState

__all__ = ["build_hr_graph", "HRAgentState"]
