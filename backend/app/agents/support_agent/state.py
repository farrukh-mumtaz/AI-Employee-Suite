from typing import List, Literal, Optional

from backend.app.core.state import AgentState

# Which support flow the current conversation has been routed into.
# "unknown" is the default until the classifier node has run.
SupportWorkflow = Literal[
    "password_reset", "order_status", "refund_request", "unknown"
]


class SupportAgentState(AgentState):
    """Support Agent state.

    Extends the shared core `AgentState` (messages, user_input, agent_response,
    agent_name) with the extra fields the support flows need. Keeping these
    fields on a subclass -- instead of editing the shared `AgentState` -- means
    other agents built on the shared scaffold are unaffected by support-specific
    data. Mirrors the pattern used by `backend/app/agents/hr_agent/state.py`.
    """

    # Set by the classifier node in nodes.py and used by graph.py to decide
    # which workflow branch (password reset / order status / refund) to run.
    workflow: SupportWorkflow

    # --- Password Reset flow fields ---
    account_email: Optional[str]
    reset_link_sent: Optional[bool]

    # --- Order Status flow fields ---
    order_id: Optional[str]
    order_status: Optional[str]

    # --- Refund Request flow fields ---
    refund_reason: Optional[str]
    # Populated by rag.py's placeholder retrieval step. Future integration
    # point for a real refund-policy knowledge base / vector store.
    refund_policy_context: Optional[List[str]]
    # Placeholder decision ("pending_manual_review", etc.) until real refund
    # eligibility / approval-workflow logic is implemented.
    refund_decision: Optional[str]
