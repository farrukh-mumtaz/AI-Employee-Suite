from langgraph.graph import StateGraph, END
from backend.app.core.state import AgentState
from backend.app.core.llm_client import get_llm

def call_llm_node(state: AgentState) -> AgentState:
    try:
        llm = get_llm()
        system_prompt = state.get("system_prompt") or "You are a helpful AI assistant."
        full_prompt = f"{system_prompt}\n\nUser: {state['user_input']}"
        response = llm.invoke(full_prompt)
        state["agent_response"] = response.content
    except Exception as e:
        state["agent_response"] = f"Sorry, something went wrong: {str(e)}"
    return state

def build_base_graph():
    graph = StateGraph(AgentState)
    graph.add_node("call_llm", call_llm_node)
    graph.set_entry_point("call_llm")
    graph.add_edge("call_llm", END)
    return graph.compile()