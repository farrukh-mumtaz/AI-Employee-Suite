# Node implementations for the HR Agent graph.
#
# Every node follows the shared scaffold's convention (see
# backend/app/core/graph.py): a plain function that takes the state dict,
# reads/writes fields on it, and returns it. The LLM is always obtained via
# the shared `get_llm()` factory so model/provider swaps happen in one place.
from backend.app.agents.hr_agent import prompts
from backend.app.agents.hr_agent.rag import retrieve_leave_policy
from backend.app.agents.hr_agent.state import HRAgentState
from backend.app.core.llm_client import get_llm


def classify_intent_node(state: HRAgentState) -> HRAgentState:
    """Entry node: decide whether this request is onboarding, a leave
    request, or unknown, and store the result on `state["workflow"]` so
    graph.py's conditional edge can route to the right branch.

    Future integration point: replace this single-shot LLM classification
    with a more robust intent-routing model, or with explicit workflow
    selection from the frontend (e.g. the user clicked "Start onboarding").
    """
    llm = get_llm()
    prompt = prompts.CLASSIFY_INTENT_PROMPT.format(user_input=state["user_input"])
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    if intent not in ("onboarding", "leave_request"):
        intent = "unknown"

    state["workflow"] = intent
    return state


# --- Employee Onboarding workflow nodes ---

def extract_employee_details_node(state: HRAgentState) -> HRAgentState:
    """Pull employee name/role/start date out of the request.

    Placeholder implementation: real extraction (structured output / a form
    upstream in the product) is not wired up yet, so we fall back to
    "Unknown" values when they're not already present on the state. Future
    integration point: replace with structured extraction (e.g. an LLM
    tool-call / function-calling step) or accept these as explicit inputs
    from an onboarding form instead of parsing free text.
    """
    state.setdefault("employee_name", "Unknown")
    state.setdefault("employee_role", "Unknown")
    state.setdefault("start_date", "Unknown")
    return state


def generate_welcome_message_node(state: HRAgentState) -> HRAgentState:
    """Generate a short welcome message for the new hire via the LLM."""
    llm = get_llm()
    prompt = prompts.ONBOARDING_WELCOME_PROMPT.format(
        employee_name=state.get("employee_name", "Unknown"),
        employee_role=state.get("employee_role", "Unknown"),
        start_date=state.get("start_date", "Unknown"),
    )
    response = llm.invoke(prompt)
    state["agent_response"] = response.content
    return state


def generate_onboarding_checklist_node(state: HRAgentState) -> HRAgentState:
    """Attach the onboarding checklist to the state.

    Placeholder implementation: uses a static template. Future integration
    point: generate/pull this from the company's HRIS or task-tracking
    system so it reflects the employee's actual role and department.
    """
    state["onboarding_checklist"] = list(prompts.ONBOARDING_CHECKLIST_TEMPLATE)
    return state


# --- Leave Request workflow nodes ---

def extract_leave_details_node(state: HRAgentState) -> HRAgentState:
    """Pull leave type / start / end dates out of the request.

    Placeholder implementation, same caveat as `extract_employee_details_node`:
    replace with structured extraction or an explicit leave-request form once
    available.
    """
    state.setdefault("leave_type", "Unspecified")
    state.setdefault("leave_start_date", "Unspecified")
    state.setdefault("leave_end_date", "Unspecified")
    return state


def retrieve_leave_policy_node(state: HRAgentState) -> HRAgentState:
    """Fetch relevant HR policy snippets for the leave request via rag.py.

    Future integration point: rag.py currently does keyword matching over a
    hardcoded list; swap in real semantic retrieval once a policy document
    store exists.
    """
    state["leave_policy_context"] = retrieve_leave_policy(state["user_input"])
    return state


def evaluate_leave_request_node(state: HRAgentState) -> HRAgentState:
    """Draft a response acknowledging the leave request.

    Placeholder implementation: the agent never auto-approves/denies leave --
    it always routes to manual HR review. Future integration point: connect
    to a real leave-balance/approval system to make (or assist a manager in
    making) the actual decision.
    """
    state["leave_decision"] = "pending_manual_review"

    llm = get_llm()
    prompt = prompts.LEAVE_REQUEST_EVALUATION_PROMPT.format(
        leave_type=state.get("leave_type", "Unspecified"),
        leave_start_date=state.get("leave_start_date", "Unspecified"),
        leave_end_date=state.get("leave_end_date", "Unspecified"),
        policy_context="\n".join(state.get("leave_policy_context") or []),
        user_input=state["user_input"],
    )
    response = llm.invoke(prompt)
    state["agent_response"] = response.content
    return state


# --- Fallback ---

def unknown_intent_node(state: HRAgentState) -> HRAgentState:
    """Handle messages that don't match either supported workflow.

    Future integration point: expand HR workflow coverage (e.g. benefits
    questions, performance reviews) and route to those instead of this
    fallback.
    """
    state["agent_response"] = (
        "I can currently help with employee onboarding and leave requests. "
        "Could you clarify which of these you need help with?"
    )
    return state
