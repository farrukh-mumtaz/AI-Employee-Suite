# Marketing Agent graph definition.
#
# Scaffold only - follows the same StateGraph + compile pattern as the
# Sales and HR agents. generate_content_node is currently a placeholder;
# real content-generation logic will replace it in a follow-up task.
from langgraph.graph import END, StateGraph

from backend.app.agents.marketing_agent.nodes import generate_content_node
from backend.app.agents.marketing_agent.state import MarketingContentState


def build_marketing_graph():
    """Build and compile the Marketing Agent graph.

    Flow (scaffold):
        generate_content -> END
    """
    graph = StateGraph(MarketingContentState)

    graph.add_node("generate_content", generate_content_node)
    graph.set_entry_point("generate_content")
    graph.add_edge("generate_content", END)

    return graph.compile()