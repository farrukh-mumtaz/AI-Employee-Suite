from backend.app.core.state import AgentState
from backend.app.core.retrieval import retrieve_relevant_docs

# This is a LangGraph node that retrieves relevant documents and adds them to the conversation
# context, so the LLM can use real company information when generating its response.
def rag_retrieval_node(state: AgentState) -> AgentState:
    relevant_docs = retrieve_relevant_docs(state["user_input"], top_k=3)
    context = "\n".join(relevant_docs)

    existing_prompt = state.get("system_prompt") or "You are a helpful AI assistant."
    state["system_prompt"] = f"{existing_prompt}\n\nRelevant company information:\n{context}"

    return state