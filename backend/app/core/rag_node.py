from backend.app.core.state import AgentState
from backend.app.core.retrieval import retrieve_relevant_docs

# This creates a RAG retrieval node that any agent can add to its graph.
# top_k is configurable, so different agents can choose how many documents to retrieve.
# This is the "finalized" reusable interface for all agent graphs.
def make_rag_node(top_k: int = 3):
    def rag_retrieval_node(state: AgentState) -> AgentState:
        relevant_docs = retrieve_relevant_docs(state["user_input"], top_k=top_k)
        context = "\n".join(relevant_docs)

        existing_prompt = state.get("system_prompt") or "You are a helpful AI assistant."
        state["system_prompt"] = f"{existing_prompt}\n\nRelevant company information:\n{context}"

        return state
    return rag_retrieval_node

# A ready-to-use default node with top_k=3, for agents that don't need custom settings.
rag_retrieval_node = make_rag_node(top_k=3)