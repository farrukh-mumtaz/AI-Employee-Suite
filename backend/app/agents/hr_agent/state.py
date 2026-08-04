from typing import List, Literal, Optional

from backend.app.core.state import AgentState

# Which HR workflow the current conversation has been routed into.
# "unknown" is the default until the classifier node has run.
HRWorkflow = Literal["onboarding", "leave_request", "unknown"]

# Outcome of evaluate_leave_request_node's auto-approval check. Read by
# graph.py's conditional edge to route to approve_leave_node or
# reject_leave_node.
LeaveDecision = Literal["approved", "rejected"]


class HRAgentState(AgentState, total=False):
    """HR Agent state.

    Extends the shared core `AgentState` (messages, user_input, agent_response,
    agent_name) with the extra fields the HR workflows need. Keeping these
    fields on a subclass -- instead of editing the shared `AgentState` -- means
    other agents built on the shared scaffold are unaffected by HR-specific data.

    `total=False` marks every field declared on *this* subclass as optional
    (per PEP 589, this does not affect the inherited `AgentState` fields,
    which remain required). That matches reality: callers construct the
    initial state with only the base `AgentState` fields, and each field
    below is filled in by a later node as the graph runs.
    """

    # Set by classify_intent_node in nodes.py and used by graph.py to decide
    # which workflow branch (onboarding vs. leave request) to run.
    workflow: HRWorkflow

    # --- Employee Onboarding workflow fields ---
    employee_name: Optional[str]
    employee_role: Optional[str]
    start_date: Optional[str]
    # Filled in by generate_onboarding_checklist_node. Placeholder logic today;
    # future integration point for a real HRIS/onboarding-system checklist.
    onboarding_checklist: Optional[List[str]]

    # --- Leave Request workflow fields ---
    leave_type: Optional[str]
    leave_start_date: Optional[str]
    leave_end_date: Optional[str]
    # Populated by extraction.py's extract_leave_reason heuristic in
    # extract_leave_details_node. Purely informational context surfaced in
    # the approve/reject response messages -- not a gating input to
    # evaluate_leave_request_node's auto-approval check.
    leave_reason: Optional[str]
    # Populated by rag.py's placeholder retrieval step. Future integration
    # point for a real leave-policy knowledge base / vector store.
    leave_policy_context: Optional[List[str]]
    # Set by evaluate_leave_request_node. Placeholder rule-based decision
    # until real leave balance / manager-approval-workflow logic exists.
    leave_decision: Optional[LeaveDecision]
