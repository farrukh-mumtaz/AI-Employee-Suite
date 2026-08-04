from backend.app.agents.marketing_agent.nodes import generate_ab_suggestion_node


def run_test(label, topic, platform, tone):
    print(f"=== {label} ===")
    state = {
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "ab_suggestion",
        "content_topic": topic, "platform": platform,
        "generated_content": None, "tone": tone,
        "campaign_goal": None, "campaign_ideas": None,
        "calendar_period": None, "content_calendar": None,
        "ab_variant_a": None, "ab_variant_b": None, "ab_rationale": None,
    }
    result = generate_ab_suggestion_node(state)
    print("Variant A:", result.get("ab_variant_a"))
    print("Variant B:", result.get("ab_variant_b"))
    print("Rationale:", result.get("ab_rationale"))
    print()


run_test("Test 1: Instagram, friendly", "new product launch", "instagram", "friendly")
run_test("Test 2: Email, urgent", "flash sale ending soon", "email", "urgent")