from typing import List, Literal, Optional

from backend.app.core.state import AgentState

# Which HR workflow the current conversation has been routed into.
# "unknown" is the default until the classifier node has run.
HRWorkflow = Literal["onboarding", "leave_request", "unknown"]


class HRAgentState(AgentState):
    """HR Agent state.

    Extends the shared core `AgentState` (messages, user_input, agent_response,
    agent_name) with the extra fields the HR workflows need. Keeping these
    fields on a subclass -- instead of editing the shared `AgentState` -- means
    other agents built on the shared scaffold are unaffected by HR-specific data.
    """

    # Set by the classifier node in nodes.py and used by graph.py to decide
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
    # Populated by rag.py's placeholder retrieval step. Future integration
    # point for a real leave-policy knowledge base / vector store.
    leave_policy_context: Optional[List[str]]
    # Placeholder decision ("pending_manual_review", etc.) until real leave
    # balance / approval-workflow logic is implemented.
    leave_decision: Optional[str]
