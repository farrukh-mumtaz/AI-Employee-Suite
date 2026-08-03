import json
from backend.app.agents.sales_agent.prompts import (
    LEAD_QUALIFICATION_PROMPT,
    FOLLOWUP_EMAIL_PROMPT,
    OBJECTION_HANDLING_PROMPT,
)

from backend.app.agents.sales_agent.prompts import (
    LEAD_QUALIFICATION_PROMPT,
    FOLLOWUP_EMAIL_PROMPT,
)
from backend.app.core.llm_client import get_llm
from backend.app.agents.sales_agent.state import SalesLeadState
from backend.app.agents.sales_agent.prompts import LEAD_QUALIFICATION_PROMPT


def lead_qualification_node(state: SalesLeadState) -> SalesLeadState:
    llm = get_llm()

    prompt = LEAD_QUALIFICATION_PROMPT.format(
        system_prompt=state.get("system_prompt") or "You are a sales assistant.",
        lead_name=state.get("lead_name", "there"),
        user_message=state["user_input"],
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["intent"] = result["intent"]
    state["agent_response"] = result["reply"]
    state["agent_name"] = "sales"
    return state

if __name__ == "__main__":
    test_state: SalesLeadState = {
        "messages": [],
        "user_input": "Hi, I am interested in your pricing",
        "agent_response": None,
        "agent_name": "sales",
        "system_prompt": "You are a sales assistant for a company.",
        "intent": None,
        "lead_name": "Ali",
    }

    result = lead_qualification_node(test_state)
    print("Result:", result)

def notify_sales_node(state: SalesLeadState) -> SalesLeadState:
    """Qualified branch: hot lead - flag for the sales team."""
    state["notified"] = True
    state["agent_response"] = (
        f"[HOT LEAD - sales team notified] {state.get('agent_response', '')}"
    )
    return state


def skip_notify_node(state: SalesLeadState) -> SalesLeadState:
    """Unqualified branch: warm/cold lead - no urgent alert needed."""
    state["notified"] = False
    return state

def draft_followup_email_node(state: SalesLeadState) -> SalesLeadState:
    """Runs after a hot lead is notified - drafts a personalized follow-up email.
    If an objection was detected earlier, the email addresses it directly."""
    llm = get_llm()

    if state.get("has_objection"):
        objection_context = f"Objection they raised: {state.get('objection_response', '')}"
        objection_instruction = "4. Gently address the objection mentioned above, building on the earlier response to it"
    else:
        objection_context = ""
        objection_instruction = ""

    prompt = FOLLOWUP_EMAIL_PROMPT.format(
        lead_name=state.get("lead_name", "there"),
        user_message=state["user_input"],
        ai_reply=state.get("agent_response", ""),
        objection_context=objection_context,
        objection_instruction=objection_instruction,
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["followup_email_subject"] = result["subject"]
    state["followup_email_body"] = result["body"]
    return state
def handle_objection_node(state: SalesLeadState) -> SalesLeadState:
    """Detects and responds to a sales objection in the lead's message."""
    llm = get_llm()

    prompt = OBJECTION_HANDLING_PROMPT.format(
        lead_name=state.get("lead_name", "there"),
        user_message=state["user_input"],
    )

    response = llm.invoke(prompt)
    result = json.loads(response.content)

    state["has_objection"] = result["has_objection"]
    state["objection_response"] = result["response"]
    return state