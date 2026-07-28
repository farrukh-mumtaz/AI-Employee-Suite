# HR Agent graph definition.
#
# Reuses the shared LangGraph scaffold's pattern (StateGraph + compile) from
# backend/app/core/graph.py, but defines its own graph shape instead of
# calling build_base_graph() directly, since the HR agent needs conditional
# routing between two workflows rather than the single linear call_llm node.
#
# Every node in nodes.py returns a partial state update (only the keys it
# changes) rather than the full state dict; StateGraph merges each node's
# return value into the running state using the default last-value-wins
# channel behavior, since HRAgentState declares no custom reducers.
from langgraph.graph import END, StateGraph

from backend.app.agents.hr_agent.nodes import (
    approve_leave_node,
    classify_intent_node,
    evaluate_leave_request_node,
    extract_employee_details_node,
    extract_leave_details_node,
    generate_onboarding_checklist_node,
    generate_welcome_message_node,
    reject_leave_node,
    retrieve_leave_policy_node,
    unknown_intent_node,
)
from backend.app.agents.hr_agent.state import HRAgentState


def _route_by_workflow(state: HRAgentState) -> str:
    """Conditional-edge selector: reads the workflow decided by
    classify_intent_node and picks which branch to run next."""
    return state.get("workflow", "unknown")


def _route_by_leave_decision(state: HRAgentState) -> str:
    """Conditional-edge selector: reads the decision made by
    evaluate_leave_request_node and picks the approve or reject branch.
    Defaults to "rejected" (manual review) for any unrecognized value so a
    future change to the decision logic can't dead-end the graph."""
    decision = state.get("leave_decision")
    return decision if decision in ("approved", "rejected") else "rejected"


def build_hr_graph():
    """Build and compile the HR Agent graph.

    Flow:
        classify_intent
            -> onboarding branch: extract_employee_details -> generate_welcome_message
               -> generate_onboarding_checklist -> END
            -> leave_request branch: extract_leave_details -> retrieve_leave_policy
               -> evaluate_leave_request
                   -> approved -> approve_leave -> END
                   -> rejected -> reject_leave -> END
            -> unknown branch: unknown_intent -> END
    """
    graph = StateGraph(HRAgentState)

    graph.add_node("classify_intent", classify_intent_node)

    # Onboarding branch
    graph.add_node("extract_employee_details", extract_employee_details_node)
    graph.add_node("generate_welcome_message", generate_welcome_message_node)
    graph.add_node("generate_onboarding_checklist", generate_onboarding_checklist_node)

    # Leave request branch
    graph.add_node("extract_leave_details", extract_leave_details_node)
    graph.add_node("retrieve_leave_policy", retrieve_leave_policy_node)
    graph.add_node("evaluate_leave_request", evaluate_leave_request_node)
    graph.add_node("approve_leave", approve_leave_node)
    graph.add_node("reject_leave", reject_leave_node)

    # Fallback branch
    graph.add_node("unknown_intent", unknown_intent_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        _route_by_workflow,
        {
            "onboarding": "extract_employee_details",
            "leave_request": "extract_leave_details",
            "unknown": "unknown_intent",
        },
    )

    # Onboarding branch wiring
    graph.add_edge("extract_employee_details", "generate_welcome_message")
    graph.add_edge("generate_welcome_message", "generate_onboarding_checklist")
    graph.add_edge("generate_onboarding_checklist", END)

    # Leave request branch wiring
    graph.add_edge("extract_leave_details", "retrieve_leave_policy")
    graph.add_edge("retrieve_leave_policy", "evaluate_leave_request")
    graph.add_conditional_edges(
        "evaluate_leave_request",
        _route_by_leave_decision,
        {
            "approved": "approve_leave",
            "rejected": "reject_leave",
        },
    )
    graph.add_edge("approve_leave", END)
    graph.add_edge("reject_leave", END)

    # Fallback branch wiring
    graph.add_edge("unknown_intent", END)

    return graph.compile()
