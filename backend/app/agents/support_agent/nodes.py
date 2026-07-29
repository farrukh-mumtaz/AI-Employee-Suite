# Node implementations for the Support Agent graph.
#
# Every node follows the shared scaffold's convention (see
# backend/app/core/graph.py): a plain function that takes the state dict,
# reads/writes fields on it, and returns it. The LLM is always obtained via
# the shared `get_llm()` factory so model/provider swaps happen in one place.
# Mirrors the structure of hr_agent/nodes.py.
import uuid
from typing import Any, Dict

from backend.app.agents.support_agent import prompts
from backend.app.agents.support_agent.rag import lookup_order_status, retrieve_refund_policy
from backend.app.agents.support_agent.state import SupportAgentState
from backend.app.core.llm_client import get_llm

# --- Ticket intake helpers ---
#
# Simple, deterministic keyword heuristic -- no LLM call -- so every
# incoming message gets a ticket immediately, before the (LLM-based, and
# therefore slower/fallible) classify_intent_node runs. Future integration
# point: replace with a real ticketing system's intake rules, or an ML
# priority model, once one exists.
_HIGH_PRIORITY_KEYWORDS = (
    "urgent", "asap", "immediately", "emergency", "critical",
    "fraud", "unauthorized", "locked out", "can't access", "cannot access",
)
_LOW_PRIORITY_KEYWORDS = (
    "just wondering", "no rush", "whenever", "just curious", "question about",
)

# Placeholder category: ticket_intake_node runs before classify_intent, so
# there's no real intent signal yet. Future integration point: refine this
# once a triage model or a real ticketing system's category rules exist --
# classify_intent_node's later, LLM-based `workflow` classification is the
# actual routing signal in the meantime.
_DEFAULT_ISSUE_CATEGORY = "General Support"


def _determine_ticket_priority(user_input: str) -> str:
    """Placeholder priority heuristic: keyword match against a small set of
    urgency signals, defaulting to "Medium" when nothing matches."""
    lowered = user_input.lower()
    if any(keyword in lowered for keyword in _HIGH_PRIORITY_KEYWORDS):
        return "High"
    if any(keyword in lowered for keyword in _LOW_PRIORITY_KEYWORDS):
        return "Low"
    return "Medium"


def ticket_intake_node(state: SupportAgentState) -> Dict[str, Any]:
    """Entry node: open a support ticket before intent classification runs.

    Every incoming request gets a ticket -- regardless of what it turns out
    to be about -- with a unique ID, "Open" status, and a placeholder
    priority/category so there's always something to track and triage even
    if classification later resolves to "unknown".

    Only fills in fields that aren't already set, and never touches any
    other key (including `user_input`) -- so all existing state is
    preserved, and re-running intake on a request that already has a ticket
    (e.g. a resumed conversation) won't mint a second ticket ID for it.
    """
    user_input = state.get("user_input") or ""
    updates: Dict[str, Any] = {}

    if not state.get("ticket_id"):
        updates["ticket_id"] = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    if not state.get("ticket_status"):
        updates["ticket_status"] = "Open"
    if not state.get("ticket_priority"):
        updates["ticket_priority"] = _determine_ticket_priority(user_input)
    if not state.get("issue_category"):
        updates["issue_category"] = _DEFAULT_ISSUE_CATEGORY

    return updates


def classify_intent_node(state: SupportAgentState) -> SupportAgentState:
    """Entry node: decide whether this request is a password reset, order
    status check, refund request, or unknown, and store the result on
    `state["workflow"]` so graph.py's conditional edge can route to the
    right branch.

    Future integration point: replace this single-shot LLM classification
    with a more robust intent-routing model, or with explicit workflow
    selection from the frontend (e.g. the user clicked "Request a refund").
    """
    llm = get_llm()
    prompt = prompts.CLASSIFY_INTENT_PROMPT.format(user_input=state["user_input"])
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    if intent not in ("password_reset", "order_status", "refund_request"):
        intent = "unknown"

    state["workflow"] = intent
    return state


# --- Password Reset workflow nodes ---

def extract_account_details_node(state: SupportAgentState) -> SupportAgentState:
    """Pull the account email out of the request.

    Placeholder implementation: real extraction (structured output / an
    authenticated session upstream in the product) is not wired up yet, so
    we fall back to "Unknown" when it's not already present on the state.
    Future integration point: replace with structured extraction or pull the
    email from the authenticated user's session instead of parsing free text.
    """
    state.setdefault("account_email", "Unknown")
    return state


def send_password_reset_node(state: SupportAgentState) -> SupportAgentState:
    """Simulate sending a password reset link and draft a response.

    Placeholder implementation: no auth system is wired up yet, so this only
    marks `reset_link_sent` as True without actually sending anything.
    Future integration point: call the real auth/identity service to
    generate and email a reset link.
    """
    state["reset_link_sent"] = True

    llm = get_llm()
    prompt = prompts.PASSWORD_RESET_PROMPT.format(
        account_email=state.get("account_email", "Unknown"),
    )
    response = llm.invoke(prompt)
    state["agent_response"] = response.content
    return state


# --- Order Status workflow nodes ---

def extract_order_details_node(state: SupportAgentState) -> SupportAgentState:
    """Pull the order ID out of the request.

    Placeholder implementation, same caveat as `extract_account_details_node`:
    replace with structured extraction or an explicit order-lookup form once
    available.
    """
    state.setdefault("order_id", "Unspecified")
    return state


def retrieve_order_status_node(state: SupportAgentState) -> SupportAgentState:
    """Fetch the current order status via rag.py's placeholder lookup.

    Future integration point: `lookup_order_status` currently returns a
    fixed placeholder string; swap in a real order-management/shipping
    system call once one exists.
    """
    state["order_status"] = lookup_order_status(state.get("order_id"))
    return state


def generate_order_status_response_node(state: SupportAgentState) -> SupportAgentState:
    """Draft a response summarizing the order status for the customer."""
    llm = get_llm()
    prompt = prompts.ORDER_STATUS_PROMPT.format(
        order_id=state.get("order_id", "Unspecified"),
        order_status=state.get("order_status", "Unknown"),
        user_input=state["user_input"],
    )
    response = llm.invoke(prompt)
    state["agent_response"] = response.content
    return state


# --- Refund Request workflow nodes ---

def extract_refund_details_node(state: SupportAgentState) -> SupportAgentState:
    """Pull the order ID and refund reason out of the request.

    Placeholder implementation, same caveat as the other extraction nodes:
    replace with structured extraction or an explicit refund-request form
    once available.
    """
    state.setdefault("order_id", "Unspecified")
    state.setdefault("refund_reason", "Unspecified")
    return state


def retrieve_refund_policy_node(state: SupportAgentState) -> SupportAgentState:
    """Fetch relevant refund policy snippets for the request via rag.py.

    Future integration point: rag.py currently does keyword matching over a
    hardcoded list; swap in real semantic retrieval once a policy document
    store exists.
    """
    state["refund_policy_context"] = retrieve_refund_policy(state["user_input"])
    return state


def evaluate_refund_request_node(state: SupportAgentState) -> SupportAgentState:
    """Draft a response acknowledging the refund request.

    Placeholder implementation: the agent never auto-approves/denies a
    refund -- it always routes to manual review. Future integration point:
    connect to a real payments/order system to make (or assist a support
    agent in making) the actual decision.
    """
    state["refund_decision"] = "pending_manual_review"

    llm = get_llm()
    prompt = prompts.REFUND_REQUEST_PROMPT.format(
        order_id=state.get("order_id", "Unspecified"),
        refund_reason=state.get("refund_reason", "Unspecified"),
        policy_context="\n".join(state.get("refund_policy_context") or []),
        user_input=state["user_input"],
    )
    response = llm.invoke(prompt)
    state["agent_response"] = response.content
    return state


# --- Fallback ---

def unknown_intent_node(state: SupportAgentState) -> SupportAgentState:
    """Handle messages that don't match any supported workflow.

    Future integration point: expand support workflow coverage (e.g.
    billing disputes, technical troubleshooting) and route to those instead
    of this fallback.
    """
    state["agent_response"] = (
        "I can currently help with password resets, order status, and "
        "refund requests. Could you clarify which of these you need help with?"
    )
    return state
