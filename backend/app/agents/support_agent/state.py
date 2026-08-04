from typing import Literal, Optional

from backend.app.core.state import AgentState

# Which support flow the current conversation has been routed into.
# "unknown" is the default until the classifier node has run.
SupportWorkflow = Literal[
    "password_reset", "order_status", "refund_request", "unknown"
]

# Priority assigned by ticket_intake_node's placeholder heuristic.
TicketPriority = Literal["Low", "Medium", "High"]


class SupportAgentState(AgentState, total=False):
    """Support Agent state.

    Extends the shared core `AgentState` (messages, user_input, agent_response,
    agent_name) with the extra fields the support flows need. Keeping these
    fields on a subclass -- instead of editing the shared `AgentState` -- means
    other agents built on the shared scaffold are unaffected by support-specific
    data. Mirrors the pattern used by `backend/app/agents/hr_agent/state.py`.

    `total=False` marks every field declared on *this* subclass as optional
    (per PEP 589, this does not affect the inherited `AgentState` fields,
    which remain required) -- callers construct the initial state with only
    the base `AgentState` fields, and each field below is filled in by a
    later node as the graph runs. Matches `HRAgentState`'s convention.
    """

    # --- Ticket intake fields (set by ticket_intake_node, which runs before
    # classify_intent as the graph's entry point) ---
    ticket_id: Optional[str]
    ticket_status: Optional[str]
    ticket_priority: Optional[TicketPriority]
    issue_category: Optional[str]

    # Set by the classifier node in nodes.py and used by graph.py to decide
    # which workflow branch (password reset / order status / refund) to run.
    workflow: SupportWorkflow

    # --- Ticket classification fields (set by ticket_classification_node,
    # which runs after ticket_intake and before classify_intent) ---
    # Business/reporting category -- distinct from `workflow` above, which
    # only exists to pick a graph branch. "Unknown" when the LLM's category
    # wasn't recognized or its confidence fell below the project threshold.
    ticket_category: Optional[str]
    ticket_category_confidence: Optional[float]

    # --- Password Reset flow fields ---
    account_email: Optional[str]
    reset_link_sent: Optional[bool]

    # --- Order Status flow fields ---
    order_id: Optional[str]
    order_status: Optional[str]

    # --- Refund Request flow fields ---
    # Retrieved refund-policy context (via the shared RAG node in
    # nodes.py's retrieve_refund_policy_node) is carried in the inherited
    # `system_prompt` field, not a dedicated field here.
    refund_reason: Optional[str]
    # Placeholder decision ("pending_manual_review", etc.) until real refund
    # eligibility / approval-workflow logic is implemented.
    refund_decision: Optional[str]
