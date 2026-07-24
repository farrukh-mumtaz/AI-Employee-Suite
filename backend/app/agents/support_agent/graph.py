# Support Agent graph definition.
#
# Reuses the shared LangGraph scaffold's pattern (StateGraph + compile) from
# backend/app/core/graph.py, but defines its own graph shape instead of
# calling build_base_graph() directly, since the Support agent needs
# conditional routing between three workflows rather than a single linear
# call_llm node. Mirrors hr_agent/graph.py.
from langgraph.graph import END, StateGraph

from backend.app.agents.support_agent.nodes import (
    classify_intent_node,
    evaluate_refund_request_node,
    extract_account_details_node,
    extract_order_details_node,
    extract_refund_details_node,
    generate_order_status_response_node,
    retrieve_order_status_node,
    retrieve_refund_policy_node,
    send_password_reset_node,
    unknown_intent_node,
)
from backend.app.agents.support_agent.state import SupportAgentState


def _route_by_workflow(state: SupportAgentState) -> str:
    """Conditional-edge selector: reads the workflow decided by
    classify_intent_node and picks which branch to run next."""
    return state.get("workflow", "unknown")


def build_support_graph():
    """Build and compile the Support Agent graph.

    Flow:
        classify_intent
            -> password_reset branch: extract_account_details
               -> send_password_reset -> END
            -> order_status branch: extract_order_details -> retrieve_order_status
               -> generate_order_status_response -> END
            -> refund_request branch: extract_refund_details -> retrieve_refund_policy
               -> evaluate_refund_request -> END
            -> unknown branch: unknown_intent -> END
    """
    graph = StateGraph(SupportAgentState)

    graph.add_node("classify_intent", classify_intent_node)

    # Password reset branch
    graph.add_node("extract_account_details", extract_account_details_node)
    graph.add_node("send_password_reset", send_password_reset_node)

    # Order status branch
    graph.add_node("extract_order_details", extract_order_details_node)
    graph.add_node("retrieve_order_status", retrieve_order_status_node)
    graph.add_node("generate_order_status_response", generate_order_status_response_node)

    # Refund request branch
    graph.add_node("extract_refund_details", extract_refund_details_node)
    graph.add_node("retrieve_refund_policy", retrieve_refund_policy_node)
    graph.add_node("evaluate_refund_request", evaluate_refund_request_node)

    # Fallback branch
    graph.add_node("unknown_intent", unknown_intent_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        _route_by_workflow,
        {
            "password_reset": "extract_account_details",
            "order_status": "extract_order_details",
            "refund_request": "extract_refund_details",
            "unknown": "unknown_intent",
        },
    )

    # Password reset branch wiring
    graph.add_edge("extract_account_details", "send_password_reset")
    graph.add_edge("send_password_reset", END)

    # Order status branch wiring
    graph.add_edge("extract_order_details", "retrieve_order_status")
    graph.add_edge("retrieve_order_status", "generate_order_status_response")
    graph.add_edge("generate_order_status_response", END)

    # Refund request branch wiring
    graph.add_edge("extract_refund_details", "retrieve_refund_policy")
    graph.add_edge("retrieve_refund_policy", "evaluate_refund_request")
    graph.add_edge("evaluate_refund_request", END)

    # Fallback branch wiring
    graph.add_edge("unknown_intent", END)

    return graph.compile()
