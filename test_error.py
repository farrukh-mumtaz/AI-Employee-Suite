from backend.app.core.graph import build_base_graph

graph = build_base_graph()

# Intentionally not providing system_prompt
result = graph.invoke({
    "messages": [],
    "user_input": "Hello",
    "agent_response": None,
    "agent_name": "test"
})

print(result["agent_response"])