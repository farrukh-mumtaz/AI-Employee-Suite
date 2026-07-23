from backend.app.core.graph import build_base_graph

graph = build_base_graph()

result = graph.invoke({
    "messages": [],
    "user_input": "Hello, what can you help me with?",
    "agent_response": None,
    "agent_name": "test"
})

print(result["agent_response"])