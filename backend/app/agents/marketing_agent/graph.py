# Marketing Agent graph definition.
#
# Follows the same conditional-routing pattern as the HR Agent: a `workflow`
# field on the state determines which branch runs, since content generation
# and campaign ideation are two distinct jobs, not a sequence.
from langgraph.graph import END, StateGraph

from backend.app.agents.marketing_agent.nodes import (
    generate_content_node,
    generate_campaign_ideas_node,
)
from backend.app.agents.marketing_agent.state import MarketingContentState


def _route_by_workflow(state: MarketingContentState) -> str:
    return state.get("workflow", "content")


def build_marketing_graph():
    """Build and compile the Marketing Agent graph.

    Flow:
        route on `workflow`:
            "content" -> generate_content -> END
            "campaign_ideas" -> generate_campaign_ideas -> END
    """
    graph = StateGraph(MarketingContentState)

    graph.add_node("generate_content", generate_content_node)
    graph.add_node("generate_campaign_ideas", generate_campaign_ideas_node)

    graph.set_conditional_entry_point(
        _route_by_workflow,
        {
            "content": "generate_content",
            "campaign_ideas": "generate_campaign_ideas",
        },
    )

    graph.add_edge("generate_content", END)
    graph.add_edge("generate_campaign_ideas", END)

    return graph.compile()