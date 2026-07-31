from backend.app.agents.marketing_agent.graph import build_marketing_graph

app = build_marketing_graph()


def run_test(label, topic, platform, tone):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [],
        "user_input": "",
        "agent_response": None,
        "agent_name": "marketing",
        "system_prompt": "You are a marketing assistant for a company.",
        "content_topic": topic,
        "platform": platform,
        "generated_content": None,
        "tone": tone,
    })
    print("Generated content:", result.get("generated_content"))
    print()


run_test("Test 1: Instagram, friendly", "new product launch", "instagram", "friendly")
run_test("Test 2: LinkedIn, professional", "quarterly company milestone", "linkedin", "professional")
run_test("Test 3: Email, friendly", "limited-time discount", "email", "friendly")