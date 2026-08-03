from backend.app.agents.marketing_agent.graph import build_marketing_graph

app = build_marketing_graph()


def run_content_test(label, topic, platform, tone):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [],
        "user_input": "",
        "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "content",
        "content_topic": topic,
        "platform": platform,
        "generated_content": None,
        "tone": tone,
        "campaign_goal": None,
        "campaign_ideas": None,
    })
    print("Generated content:", result.get("generated_content"))
    print("Campaign ideas (should be None):", result.get("campaign_ideas"))
    print()


def run_campaign_test(label, goal, topic):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [],
        "user_input": "",
        "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "campaign_ideas",
        "content_topic": topic,
        "platform": None,
        "generated_content": None,
        "tone": None,
        "campaign_goal": goal,
        "campaign_ideas": None,
    })
    print("Campaign ideas:", result.get("campaign_ideas"))
    print("Generated content (should be None):", result.get("generated_content"))
    print()


run_content_test("Test 1: Content workflow", "new product launch", "instagram", "friendly")
run_campaign_test("Test 2: Campaign ideas workflow", "increase signups", "new mobile app")

