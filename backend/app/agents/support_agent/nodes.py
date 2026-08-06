# Node implementations for the Support Agent graph.
#
# Every node follows the shared scaffold's convention (see
# backend/app/core/graph.py): a plain function that takes the state dict and
# returns updates to it. The LLM is always obtained via the shared
# `get_llm()` factory so model/provider swaps happen in one place.
#
# Nodes return a *partial* update dict (only the keys they change) rather
# than mutating the input `state` and returning it whole -- the
# LangGraph-recommended pattern, mirroring hr_agent/nodes.py.
import json
import logging
import uuid
from typing import Any, Dict

from backend.app.agents.support_agent import prompts
from backend.app.agents.support_agent.rag import lookup_order_status
from backend.app.agents.support_agent.state import SupportAgentState
from backend.app.core.llm_client import get_llm
from backend.app.core.rag_node import rag_retrieval_node

logger = logging.getLogger(__name__)


def _invoke_llm(prompt: str, *, fallback: str) -> str:
    """Call the LLM and return its text content, or `fallback` if the call
    fails or returns something unusable.

    Mirrors hr_agent.nodes._invoke_llm: centralizes LLM error handling so
    every node degrades gracefully (network errors, missing/invalid API key,
    provider outage, rate limiting, an unexpectedly empty response) instead
    of letting the whole graph invocation crash on a transient failure.
    """
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = getattr(response, "content", None)
        if not content or not str(content).strip():
            raise ValueError("LLM returned an empty response")
        return str(content)
    except Exception:
        logger.exception("Support agent LLM call failed; using fallback response")
        return fallback


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

# --- Ticket classification (ticket_classification_node) ---
#
# Business/reporting categories -- distinct from classify_intent_node's
# `workflow` values, which only exist to pick a graph branch. No project-wide
# confidence threshold exists anywhere else in the repo (checked HR, Sales,
# Marketing); this is a new, locally-scoped constant, same pattern as the
# priority keyword sets above.
_TICKET_CATEGORIES = (
    "Refund",
    "Password Reset",
    "Billing",
    "Technical Issue",
    "Account Issue",
    "Order Status",
    "General Inquiry",
)
_TICKET_CATEGORY_CONFIDENCE_THRESHOLD = 0.6


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


def ticket_classification_node(state: SupportAgentState) -> Dict[str, Any]:
    """Classify the ticket into a business/reporting category with a
    confidence score, independent of classify_intent_node's routing
    decision -- runs right after ticket_intake, before the graph forks on
    `workflow`, so it never influences which branch the request takes.

    Uses the same strict-JSON LLM response convention as
    sales_agent.lead_qualification_node / marketing_agent.generate_content_node
    (classify_intent_node's single-bare-word format can't carry a numeric
    confidence). Falls back to "Unknown" -- both when the LLM's chosen
    category isn't one of the recognized ones, and when its confidence is
    below `_TICKET_CATEGORY_CONFIDENCE_THRESHOLD` -- so low-confidence or
    malformed classifications never masquerade as a real category.
    """
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return {"ticket_category": "Unknown", "ticket_category_confidence": 0.0}

    prompt = prompts.TICKET_CLASSIFICATION_PROMPT.format(user_input=user_input)
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        result = json.loads(response.content)
        category = str(result.get("category", "")).strip()
        confidence = float(result.get("confidence", 0.0))
    except Exception:
        logger.exception("Ticket classification failed; defaulting to Unknown")
        return {"ticket_category": "Unknown", "ticket_category_confidence": 0.0}

    if category not in _TICKET_CATEGORIES or confidence < _TICKET_CATEGORY_CONFIDENCE_THRESHOLD:
        category = "Unknown"

    return {"ticket_category": category, "ticket_category_confidence": confidence}


def classify_intent_node(state: SupportAgentState) -> Dict[str, Any]:
    """Entry node: decide whether this request is a password reset, order
    status check, refund request, or unknown, and store the result on
    `state["workflow"]` so graph.py's conditional edge can route to the
    right branch.

    Future integration point: replace this single-shot LLM classification
    with a more robust intent-routing model, or with explicit workflow
    selection from the frontend (e.g. the user clicked "Request a refund").
    """
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        # Nothing to classify -- avoid a wasted LLM call and let the
        # fallback branch ask the user to clarify.
        return {"workflow": "unknown"}

    prompt = prompts.CLASSIFY_INTENT_PROMPT.format(user_input=user_input)
    raw_intent = _invoke_llm(prompt, fallback="unknown")
    intent = raw_intent.strip().lower()

    if intent not in ("password_reset", "order_status", "refund_request"):
        intent = "unknown"

    return {"workflow": intent}


# --- Password Reset workflow nodes ---

def extract_account_details_node(state: SupportAgentState) -> Dict[str, Any]:
    """Pull the account email out of the request.

    Placeholder implementation: real extraction (structured output / an
    authenticated session upstream in the product) is not wired up yet, so
    we fall back to "Unknown" when it's not already present on the state.
    Future integration point: replace with structured extraction or pull the
    email from the authenticated user's session instead of parsing free text.
    """
    if state.get("account_email"):
        return {}
    return {"account_email": "Unknown"}


def send_password_reset_node(state: SupportAgentState) -> Dict[str, Any]:
    """Simulate sending a password reset link and draft a response.

    Placeholder implementation: no auth system is wired up yet, so this only
    marks `reset_link_sent` as True without actually sending anything.
    Future integration point: call the real auth/identity service to
    generate and email a reset link.
    """
    account_email = state.get("account_email", "Unknown")
    prompt = prompts.PASSWORD_RESET_PROMPT.format(account_email=account_email)
    fallback = (
        f"A password reset link has been sent to {account_email}. "
        "Please check your inbox (and spam folder) shortly."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"reset_link_sent": True, "agent_response": content}


# --- Order Status workflow nodes ---

def extract_order_details_node(state: SupportAgentState) -> Dict[str, Any]:
    """Pull the order ID out of the request.

    Placeholder implementation, same caveat as `extract_account_details_node`:
    replace with structured extraction or an explicit order-lookup form once
    available.
    """
    if state.get("order_id"):
        return {}
    return {"order_id": "Unspecified"}


def retrieve_order_status_node(state: SupportAgentState) -> Dict[str, Any]:
    """Fetch the current order status via rag.py's placeholder lookup.

    Future integration point: `lookup_order_status` currently returns a
    fixed placeholder string; swap in a real order-management/shipping
    system call once one exists.
    """
    return {"order_status": lookup_order_status(state.get("order_id"))}


def generate_order_status_response_node(state: SupportAgentState) -> Dict[str, Any]:
    """Draft a response summarizing the order status for the customer."""
    prompt = prompts.ORDER_STATUS_PROMPT.format(
        order_id=state.get("order_id", "Unspecified"),
        order_status=state.get("order_status", "Unknown"),
        user_input=state.get("user_input", ""),
    )
    fallback = (
        f"Thanks for reaching out -- here's the latest on order "
        f"{state.get('order_id', 'Unspecified')}: "
        f"{state.get('order_status', 'Unknown')}."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"agent_response": content}


# --- Refund Request workflow nodes ---

def extract_refund_details_node(state: SupportAgentState) -> Dict[str, Any]:
    """Pull the order ID and refund reason out of the request.

    Placeholder implementation, same caveat as the other extraction nodes:
    replace with structured extraction or an explicit refund-request form
    once available.
    """
    updates: Dict[str, Any] = {}
    if not state.get("order_id"):
        updates["order_id"] = "Unspecified"
    if not state.get("refund_reason"):
        updates["refund_reason"] = "Unspecified"
    return updates


def retrieve_refund_policy_node(state: SupportAgentState) -> Dict[str, Any]:
    """Fetch relevant refund policy context via the shared RAG node
    (backend/app/core/rag_node.py), which retrieves from the real pgvector
    document store and merges the result into `system_prompt`.

    Wrapped in try/except so a retrieval/embedding failure degrades
    gracefully instead of crashing the graph -- mirrors
    retrieve_leave_policy_node's pattern in hr_agent/nodes.py.
    """
    try:
        updated_state = rag_retrieval_node(dict(state))
    except Exception:
        logger.exception("Refund policy retrieval failed; continuing with no context")
        return {}
    return {"system_prompt": updated_state.get("system_prompt")}


def evaluate_refund_request_node(state: SupportAgentState) -> Dict[str, Any]:
    """Draft a response acknowledging the refund request.

    Placeholder implementation: the agent never auto-approves/denies a
    refund -- it always routes to manual review. Future integration point:
    connect to a real payments/order system to make (or assist a support
    agent in making) the actual decision.
    """
    prompt = prompts.REFUND_REQUEST_PROMPT.format(
        order_id=state.get("order_id", "Unspecified"),
        refund_reason=state.get("refund_reason", "Unspecified"),
        policy_context=state.get("system_prompt") or "",
        user_input=state.get("user_input", ""),
    )
    fallback = (
        "Your refund request has been submitted for manual review. Our team "
        "will follow up with you shortly."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"refund_decision": "pending_manual_review", "agent_response": content}


# --- Fallback ---

def unknown_intent_node(state: SupportAgentState) -> Dict[str, Any]:
    """Handle messages that don't match any supported workflow.

    Future integration point: expand support workflow coverage (e.g.
    billing disputes, technical troubleshooting) and route to those instead
    of this fallback.
    """
    return {
        "agent_response": (
            "I can currently help with password resets, order status checks, "
            "and submitting new refund requests. I'm not yet able to answer "
            "general policy questions or check the status of an existing "
            "request -- please reach out to support directly for those. "
            "Could you tell me more about what you need?"
        )
    }
