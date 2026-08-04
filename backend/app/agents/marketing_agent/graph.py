# Marketing Agent graph definition.
#
# Follows the same conditional-routing pattern as the HR Agent: a `workflow`
# field on the state determines which branch runs, since content generation,
# campaign ideation, content calendars, and A/B suggestions are distinct
# jobs, not a sequence.
from langgraph.graph import END, StateGraph

from backend.app.agents.marketing_agent.nodes import (
    generate_content_node,
    generate_campaign_ideas_node,
    generate_content_calendar_node,
    generate_ab_suggestion_node,
)
from backend.app.agents.marketing_agent.state import MarketingContentState


def _route_by_workflow(state: MarketingContentState) -> str:
    valid_workflows = {"content", "campaign_ideas", "content_calendar", "ab_suggestion"}
    workflow = state.get("workflow")
    return workflow if workflow in valid_workflows else "content"

def build_marketing_graph():
    """Build and compile the Marketing Agent graph.

    Flow:
        route on `workflow`:
            "content" -> generate_content -> END
            "campaign_ideas" -> generate_campaign_ideas -> END
            "content_calendar" -> generate_content_calendar -> END
            "ab_suggestion" -> generate_ab_suggestion -> END
    """
    graph = StateGraph(MarketingContentState)

    graph.add_node("generate_content", generate_content_node)
    graph.add_node("generate_campaign_ideas", generate_campaign_ideas_node)
    graph.add_node("generate_content_calendar", generate_content_calendar_node)
    graph.add_node("generate_ab_suggestion", generate_ab_suggestion_node)

    graph.set_conditional_entry_point(
        _route_by_workflow,
        {
            "content": "generate_content",
            "campaign_ideas": "generate_campaign_ideas",
            "content_calendar": "generate_content_calendar",
            "ab_suggestion": "generate_ab_suggestion",
        },
    )

    graph.add_edge("generate_content", END)
    graph.add_edge("generate_campaign_ideas", END)
    graph.add_edge("generate_content_calendar", END)
    graph.add_edge("generate_ab_suggestion", END)

    return graph.compile()