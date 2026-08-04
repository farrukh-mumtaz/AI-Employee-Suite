from backend.app.agents.marketing_agent.nodes import generate_content_calendar_node


def run_test(label, topic, period):
    print(f"=== {label} ===")
    state = {
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "content_calendar",
        "content_topic": topic, "platform": None,
        "generated_content": None, "tone": None,
        "campaign_goal": None, "campaign_ideas": None,
        "calendar_period": period, "content_calendar": None,
    }
    result = generate_content_calendar_node(state)
    for entry in result.get("content_calendar", []):
        print(f"  {entry.get('day')} ({entry.get('platform')}): {entry.get('idea')}")
    print()


run_test("Test 1: 1 week, product launch", "new fitness app launch", "1 week")
run_test("Test 2: 5 days, holiday sale", "winter holiday sale", "5 days")