from backend.app.agents.marketing_agent.nodes import generate_campaign_ideas_node


def run_test(label, goal, topic):
    print(f"=== {label} ===")
    state = {
        "messages": [],
        "user_input": "",
        "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "content_topic": topic,
        "platform": None,
        "generated_content": None,
        "tone": None,
        "campaign_goal": goal,
        "campaign_ideas": None,
    }
    result = generate_campaign_ideas_node(state)
    for i, idea in enumerate(result.get("campaign_ideas", []), 1):
        print(f"  Idea {i}: {idea}")
    print()


run_test("Test 1: Increase signups", "increase signups", "new mobile app")
run_test("Test 2: Launch awareness", "launch awareness", "eco-friendly water bottle")