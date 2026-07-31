from backend.app.core.graph import build_base_graph

graph = build_base_graph()

result = graph.invoke({
    "messages": [],
    "user_input": "What's our leave policy?",
    "agent_response": None,
    "agent_name": "hr",
    "system_prompt": "You are an HR assistant for a tech company. Answer employee questions about policies clearly and briefly."
})

print(result["agent_response"])