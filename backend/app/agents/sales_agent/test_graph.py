from backend.app.agents.sales_agent.graph import build_sales_graph

app = build_sales_graph()

# Test 1: Hot lead -> should go through notify_sales
print("=== Test 1: Hot lead ===")
result_hot = app.invoke({
    "messages": [],
    "user_input": "Hi, I am interested in your pricing",
    "agent_response": None,
    "agent_name": "sales",
    "system_prompt": "You are a sales assistant for a company.",
    "intent": None,
    "lead_name": "Ali",
    "notified": None,
})
print("Result:", result_hot)
print()

# Test 2: Cold lead -> should go through skip_notify
print("=== Test 2: Cold lead ===")
result_cold = app.invoke({
    "messages": [],
    "user_input": "Just browsing, not looking to buy anything right now",
    "agent_response": None,
    "agent_name": "sales",
    "system_prompt": "You are a sales assistant for a company.",
    "intent": None,
    "lead_name": "Sara",
    "notified": None,
})
print("Result:", result_cold)