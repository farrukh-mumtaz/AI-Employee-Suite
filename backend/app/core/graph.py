from langgraph.graph import StateGraph, END
from backend.app.core.state import AgentState
from backend.app.core.llm_client import get_llm

def call_llm_node(state: AgentState) -> AgentState:
    llm = get_llm()
    response = llm.invoke(state["user_input"])
    state["agent_response"] = response.content
    return state

def build_base_graph():
    graph = StateGraph(AgentState)
    graph.add_node("call_llm", call_llm_node)
    graph.set_entry_point("call_llm")
    graph.add_edge("call_llm", END)
    return graph.compile()