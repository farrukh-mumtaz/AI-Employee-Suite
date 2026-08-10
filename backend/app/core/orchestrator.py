# Top-level orchestration graph.
#
# Single entry point that decides whether an incoming message belongs to the
# HR Agent or the Support Agent, then runs the corresponding graph exactly as
# it already exists (backend/app/agents/hr_agent/graph.py,
# backend/app/agents/support_agent/graph.py) -- this module never inspects or
# duplicates either agent's internal workflow/classification logic, it only
# picks which already-compiled graph to invoke.
#
# Mirrors the classify -> conditional_edges shape already used inside both
# agent graphs (see hr_agent/graph.py's `_route_by_workflow` and
# support_agent/graph.py's `_route_by_workflow`).
import logging
from typing import Any, Dict, Literal, Optional

from langgraph.graph import END, StateGraph

from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.agents.hr_agent.state import HRAgentState
from backend.app.agents.support_agent.graph import build_support_graph
from backend.app.agents.support_agent.state import SupportAgentState
from backend.app.core.llm_client import get_llm
from backend.app.core.state import AgentState

logger = logging.getLogger(__name__)

TargetAgent = Literal["hr", "support"]

ROUTE_AGENT_PROMPT = """You are a routing classifier for a company's internal AI assistants.
Read the user's message and decide which assistant should handle it.

Respond with exactly one word, lowercase, no punctuation:
- "hr" if the message is about employee onboarding, new hires, or an
  employee submitting a leave/time-off request.
- "support" if the message is about a customer support ticket: password
  resets, order status, refunds, or account issues.

User message:
{user_input}
"""


class OrchestratorState(AgentState, total=False):
    """Top-level orchestrator state.

    Carries only what's needed to pick a branch (`target_agent`) plus the
    shared `AgentState` fields both sub-graphs accept as input. The full
    HR/Support-specific state produced once a sub-graph runs is stored
    verbatim under `hr_result` / `support_result` rather than merged into
    this TypedDict, so this module never needs to know either agent's
    internal field names.
    """

    target_agent: TargetAgent
    hr_result: Optional[HRAgentState]
    support_result: Optional[SupportAgentState]


_hr_graph = build_hr_graph()
_support_graph = build_support_graph()


def classify_target_agent_node(state: OrchestratorState) -> Dict[str, Any]:
    """Entry node: decide whether HR or Support should handle this message.

    No signal (empty input) or an LLM failure/unrecognized reply both fall
    back to "support" -- unlike HR's graph, every Support request creates a
    ticket regardless of workflow (see support_agent/graph.py's
    ticket_intake/ticket_classification steps), so an uncertain message is
    never silently dropped: it still gets a ticket for manual follow-up.
    """
    user_input = (state.get("user_input") or "").strip()
    target: TargetAgent = "support"

    if user_input:
        try:
            llm = get_llm()
            response = llm.invoke(ROUTE_AGENT_PROMPT.format(user_input=user_input))
            content = str(getattr(response, "content", "") or "").strip().lower()
            if content in ("hr", "support"):
                target = content
        except Exception:
            logger.exception("Orchestrator routing LLM call failed; defaulting to support")

    return {"target_agent": target}


def _route_by_target_agent(state: OrchestratorState) -> str:
    return state.get("target_agent", "support")


def run_hr_agent_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run the existing HR Agent graph, unchanged, and store its final state."""
    hr_state: HRAgentState = {
        "messages": state.get("messages", []),
        "user_input": state["user_input"],
        "agent_response": None,
        "agent_name": "hr_agent",
    }
    return {"hr_result": _hr_graph.invoke(hr_state)}


def run_support_agent_node(state: OrchestratorState) -> Dict[str, Any]:
    """Run the existing Support Agent graph, unchanged, and store its final state."""
    support_state: SupportAgentState = {
        "messages": state.get("messages", []),
        "user_input": state["user_input"],
        "agent_response": None,
        "agent_name": "support_agent",
    }
    return {"support_result": _support_graph.invoke(support_state)}


def build_orchestrator_graph():
    """Build and compile the top-level orchestration graph.

    Flow:
        classify_target_agent
            -> hr -> run_hr_agent -> END
            -> support -> run_support_agent -> END
    """
    graph = StateGraph(OrchestratorState)

    graph.add_node("classify_target_agent", classify_target_agent_node)
    graph.add_node("run_hr_agent", run_hr_agent_node)
    graph.add_node("run_support_agent", run_support_agent_node)

    graph.set_entry_point("classify_target_agent")
    graph.add_conditional_edges(
        "classify_target_agent",
        _route_by_target_agent,
        {
            "hr": "run_hr_agent",
            "support": "run_support_agent",
        },
    )
    graph.add_edge("run_hr_agent", END)
    graph.add_edge("run_support_agent", END)

    return graph.compile()
