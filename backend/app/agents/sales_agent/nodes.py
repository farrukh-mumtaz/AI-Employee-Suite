import json
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