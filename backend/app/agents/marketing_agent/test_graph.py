from backend.app.agents.marketing_agent.graph import build_marketing_graph

app = build_marketing_graph()


def run_content_test(label, topic, platform, tone):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "content", "content_topic": topic, "platform": platform,
        "generated_content": None, "tone": tone,
        "campaign_goal": None, "campaign_ideas": None,
    })
    print("Content:", result.get("generated_content"))
    print()


def run_campaign_test(label, goal, topic):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [], "user_input": None, "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "workflow": "campaign_ideas", "content_topic": topic, "platform": None,
        "generated_content": None, "tone": None,
        "campaign_goal": goal, "campaign_ideas": None,
    })
    ideas = result.get("campaign_ideas", [])
    print(f"Ideas ({len(ideas)}):")
    for i, idea in enumerate(ideas, 1):
        print(f"  {i}. {idea}")
    print()


# Normal cases
run_content_test("Test 1: Instagram, friendly", "new product launch", "instagram", "friendly")
run_campaign_test("Test 2: Increase signups", "increase signups", "new mobile app")

# Edge cases
run_content_test("Test 3: Missing tone", "holiday sale", "twitter", None)
run_content_test("Test 4: Vague topic", "stuff", "instagram", "friendly")
run_campaign_test("Test 5: Very specific/niche goal", "get 50 more B2B leads from dentists in rural areas this quarter", "teeth whitening kits")
run_content_test("Test 6: Serious/sensitive topic", "company layoffs announcement", "linkedin", "professional")