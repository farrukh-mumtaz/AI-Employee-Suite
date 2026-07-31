from backend.app.agents.marketing_agent.graph import build_marketing_graph

app = build_marketing_graph()

result = app.invoke({
    "messages": [],
    "user_input": "",
    "agent_response": None,
    "agent_name": "marketing",
    "system_prompt": "You are a marketing assistant for a company.",
    "content_topic": "new product launch",
    "platform": "instagram",
    "generated_content": None,
    "tone": "friendly",
})

print("Result:", result)