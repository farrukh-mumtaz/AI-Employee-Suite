from backend.app.core.graph import build_base_graph

graph = build_base_graph()

result = graph.invoke({
    "messages": [],
    "user_input": "What pricing plans do you offer?",
    "agent_response": None,
    "agent_name": "sales",
    "system_prompt": "You are a friendly sales assistant. Answer questions about pricing and product features persuasively but honestly."
})

print(result["agent_response"])