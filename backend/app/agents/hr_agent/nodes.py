# Node implementations for the HR Agent graph.
#
# Every node follows the shared scaffold's convention (see
# backend/app/core/graph.py): a plain function that takes the state dict and
# returns updates to it. The LLM is always obtained via the shared
# `get_llm()` factory so model/provider swaps happen in one place.
#
# Unlike the original version, nodes here return a *partial* update dict
# (only the keys they change) instead of mutating the input `state` and
# returning it whole. This is the LangGraph-recommended pattern: the graph
# runtime merges each node's return value into the running state, so nodes
# don't need to see or preserve fields they don't touch, and never risk
# corrupting state shared with other in-flight branches.
import logging
from typing import Any, Dict

from backend.app.agents.hr_agent import extraction, prompts
from backend.app.agents.hr_agent.rag import retrieve_leave_policy
from backend.app.agents.hr_agent.state import HRAgentState
from backend.app.core.llm_client import get_llm

logger = logging.getLogger(__name__)


def _invoke_llm(prompt: str, *, fallback: str) -> str:
    """Call the LLM and return its text content, or `fallback` if the call
    fails or returns something unusable.

    Centralizing this means every node degrades gracefully (network errors,
    missing/invalid API key, provider outage, rate limiting, an unexpectedly
    empty response) instead of letting the whole graph invocation crash on
    what is, from the user's perspective, a transient failure.
    """
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = getattr(response, "content", None)
        if not content or not str(content).strip():
            raise ValueError("LLM returned an empty response")
        return str(content)
    except Exception:
        logger.exception("HR agent LLM call failed; using fallback response")
        return fallback


def classify_intent_node(state: HRAgentState) -> Dict[str, Any]:
    """Entry node: decide whether this request is onboarding, a leave
    request, or unknown, and store the result on `state["workflow"]` so
    graph.py's conditional edge can route to the right branch.

    Future integration point: replace this single-shot LLM classification
    with a more robust intent-routing model, or with explicit workflow
    selection from the frontend (e.g. the user clicked "Start onboarding").
    """
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        # Nothing to classify -- avoid a wasted LLM call and let the
        # fallback branch ask the user to clarify.
        return {"workflow": "unknown"}

    prompt = prompts.CLASSIFY_INTENT_PROMPT.format(user_input=user_input)
    raw_intent = _invoke_llm(prompt, fallback="unknown")
    intent = raw_intent.strip().lower()

    if intent not in ("onboarding", "leave_request"):
        intent = "unknown"

    return {"workflow": intent}


# --- Employee Onboarding workflow nodes ---


def extract_employee_details_node(state: HRAgentState) -> Dict[str, Any]:
    """Pull employee name/role/start date out of the request.

    Uses simple regex/keyword heuristics (see extraction.py) and only falls
    back to "Unknown" when nothing can be found. Fields already present on
    the incoming state (e.g. supplied by an upstream form) are left as-is.

    Future integration point: replace with structured extraction (e.g. an
    LLM tool-call / function-calling step) or accept these as explicit
    inputs from an onboarding form instead of parsing free text.
    """
    user_input = state.get("user_input") or ""
    updates: Dict[str, Any] = {}

    if not state.get("employee_name"):
        updates["employee_name"] = extraction.extract_name(user_input) or "Unknown"
    if not state.get("employee_role"):
        updates["employee_role"] = extraction.extract_role(user_input) or "Unknown"
    if not state.get("start_date"):
        dates = extraction.extract_dates(user_input, max_dates=1)
        updates["start_date"] = dates[0] if dates else "Unknown"

    return updates


def generate_welcome_message_node(state: HRAgentState) -> Dict[str, Any]:
    """Generate a short welcome message for the new hire via the LLM."""
    employee_name = state.get("employee_name") or "Unknown"
    employee_role = state.get("employee_role") or "Unknown"
    start_date = state.get("start_date") or "Unknown"

    prompt = prompts.ONBOARDING_WELCOME_PROMPT.format(
        employee_name=employee_name,
        employee_role=employee_role,
        start_date=start_date,
    )
    role_clause = f" as {employee_role}" if employee_role != "Unknown" else ""
    fallback = (
        f"Welcome, {employee_name}! We're excited to have you join us"
        f"{role_clause}. HR will be in touch shortly to guide you through "
        "onboarding."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"agent_response": content}


def generate_onboarding_checklist_node(state: HRAgentState) -> Dict[str, Any]:
    """Attach the onboarding checklist to the state.

    Placeholder implementation: uses a static template. Future integration
    point: generate/pull this from the company's HRIS or task-tracking
    system so it reflects the employee's actual role and department.
    """
    return {"onboarding_checklist": list(prompts.ONBOARDING_CHECKLIST_TEMPLATE)}


# --- Leave Request workflow nodes ---


def extract_leave_details_node(state: HRAgentState) -> Dict[str, Any]:
    """Pull leave type / start / end dates out of the request.

    Uses simple regex/keyword heuristics (see extraction.py), same caveat as
    `extract_employee_details_node`: replace with structured extraction or
    an explicit leave-request form once available.
    """
    user_input = state.get("user_input") or ""
    updates: Dict[str, Any] = {}

    if not state.get("leave_type"):
        updates["leave_type"] = extraction.extract_leave_type(user_input) or "Unspecified"

    need_start = not state.get("leave_start_date")
    need_end = not state.get("leave_end_date")
    if need_start or need_end:
        dates = extraction.extract_dates(user_input, max_dates=2)
        if need_start:
            updates["leave_start_date"] = dates[0] if len(dates) >= 1 else "Unspecified"
        if need_end:
            if len(dates) >= 2:
                updates["leave_end_date"] = dates[1]
            elif len(dates) == 1:
                # Only one date mentioned -- assume a single-day request.
                updates["leave_end_date"] = dates[0]
            else:
                updates["leave_end_date"] = "Unspecified"

    return updates


def retrieve_leave_policy_node(state: HRAgentState) -> Dict[str, Any]:
    """Fetch relevant HR policy snippets for the leave request via rag.py.

    Future integration point: rag.py currently does keyword matching over a
    hardcoded list; swap in real semantic retrieval once a policy document
    store exists.
    """
    try:
        policy_context = retrieve_leave_policy(state.get("user_input") or "")
    except Exception:
        logger.exception("Leave policy retrieval failed; continuing with no context")
        policy_context = []

    return {"leave_policy_context": policy_context}


def evaluate_leave_request_node(state: HRAgentState) -> Dict[str, Any]:
    """Decide whether the leave request can be auto-approved.

    Deterministic, rule-based placeholder: a request auto-approves only when
    the earlier extraction step was able to identify the leave type and both
    dates. Anything left "Unspecified" can't be responsibly evaluated, so it
    is routed to manual HR review instead ("rejected" here is a routing
    label, not a denial -- see reject_leave_node). Future integration point:
    replace with a real approval engine (leave balances, manager sign-off,
    the actual policy store) once one exists; graph.py routes on whatever
    this returns without caring how the decision was made.
    """
    leave_type = state.get("leave_type", "Unspecified")
    leave_start_date = state.get("leave_start_date", "Unspecified")
    leave_end_date = state.get("leave_end_date", "Unspecified")

    is_fully_specified = "Unspecified" not in (leave_type, leave_start_date, leave_end_date)
    decision = "approved" if is_fully_specified else "rejected"

    return {"leave_decision": decision}


def approve_leave_node(state: HRAgentState) -> Dict[str, Any]:
    """Terminal node for the leave workflow's "approved" branch: draft a
    confirmation message for the employee."""
    prompt = prompts.LEAVE_REQUEST_APPROVED_PROMPT.format(
        leave_type=state.get("leave_type", "Unspecified"),
        leave_start_date=state.get("leave_start_date", "Unspecified"),
        leave_end_date=state.get("leave_end_date", "Unspecified"),
        policy_context="\n".join(state.get("leave_policy_context") or []),
        user_input=state.get("user_input", ""),
    )
    fallback = (
        f"Good news -- your {state.get('leave_type', 'leave')} request "
        f"from {state.get('leave_start_date', 'Unspecified')} to "
        f"{state.get('leave_end_date', 'Unspecified')} has been approved."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"agent_response": content}


def reject_leave_node(state: HRAgentState) -> Dict[str, Any]:
    """Terminal node for the leave workflow's "rejected" branch: let the
    employee know the request needs manual HR review. This is reached when
    the request couldn't be fully understood, not when HR has actually
    declined it -- the message must not read as a denial."""
    prompt = prompts.LEAVE_REQUEST_REJECTED_PROMPT.format(
        leave_type=state.get("leave_type", "Unspecified"),
        leave_start_date=state.get("leave_start_date", "Unspecified"),
        leave_end_date=state.get("leave_end_date", "Unspecified"),
        policy_context="\n".join(state.get("leave_policy_context") or []),
        user_input=state.get("user_input", ""),
    )
    fallback = (
        "We weren't able to automatically process your leave request because "
        "some details were missing or unclear. It has been forwarded to HR "
        "for manual review."
    )
    content = _invoke_llm(prompt, fallback=fallback)
    return {"agent_response": content}


# --- Fallback ---


def unknown_intent_node(state: HRAgentState) -> Dict[str, Any]:
    """Handle messages that don't match either supported workflow.

    Future integration point: expand HR workflow coverage (e.g. benefits
    questions, performance reviews) and route to those instead of this
    fallback.
    """
    return {
        "agent_response": (
            "I can currently help with employee onboarding and leave requests. "
            "Could you clarify which of these you need help with?"
        )
    }
