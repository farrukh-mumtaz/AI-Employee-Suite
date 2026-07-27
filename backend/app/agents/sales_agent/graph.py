# Sales Agent graph definition.
#
# Reuses the shared LangGraph scaffold's pattern (StateGraph + compile) from
# backend/app/core/graph.py, but defines its own graph shape instead of
# calling build_base_graph() directly, since the Sales Agent needs conditional
# routing between qualified and unqualified leads.
from langgraph.graph import END, StateGraph

from backend.app.agents.sales_agent.nodes import (
    lead_qualification_node,
    notify_sales_node,
    skip_notify_node,
)
from backend.app.agents.sales_agent.state import SalesLeadState


def _route_by_qualification(state: SalesLeadState) -> str:
    """Conditional-edge selector: reads the intent classified by
    lead_qualification_node and picks which branch to run next."""
    return "qualified" if state.get("intent") == "hot" else "unqualified"


def build_sales_graph():
    """Build and compile the Sales Agent graph.

    Flow:
        lead_qualification
            -> qualified branch (hot lead): notify_sales -> END
            -> unqualified branch (warm/cold lead): skip_notify -> END
    """
    graph = StateGraph(SalesLeadState)

    graph.add_node("lead_qualification", lead_qualification_node)
    graph.add_node("notify_sales", notify_sales_node)
    graph.add_node("skip_notify", skip_notify_node)

    graph.set_entry_point("lead_qualification")

    graph.add_conditional_edges(
        "lead_qualification",
        _route_by_qualification,
        {
            "qualified": "notify_sales",
            "unqualified": "skip_notify",
        },
    )

    graph.add_edge("notify_sales", END)
    graph.add_edge("skip_notify", END)

    return graph.compile()