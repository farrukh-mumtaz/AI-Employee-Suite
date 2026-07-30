from backend.app.agents.sales_agent.graph import build_sales_graph

app = build_sales_graph()


def run_test(label, name, message):
    print(f"=== {label} ===")
    result = app.invoke({
        "messages": [],
        "user_input": message,
        "agent_response": None,
        "agent_name": "sales",
        "system_prompt": "You are a sales assistant for a company.",
        "intent": None,
        "lead_name": name,
        "notified": None,
        "followup_email_subject": None,
        "followup_email_body": None,
    })
    print("Intent:", result.get("intent"))
    print("Notified:", result.get("notified"))
    print("Agent reply:", result.get("agent_response"))
    print("Follow-up subject:", result.get("followup_email_subject"))
    print("Follow-up body:", result.get("followup_email_body"))
    print()
    return result


# Test 1: Clear hot lead
run_test("Test 1: Hot lead (pricing)", "Ali", "Hi, I am interested in your pricing")

# Test 2: Clear cold lead
run_test("Test 2: Cold lead (browsing)", "Sara", "Just browsing, not looking to buy anything right now")

# Test 3: Vague/short message
run_test("Test 3: Vague message", "Zain", "hey")

# Test 4: Warm lead (interested but not urgent)
run_test("Test 4: Warm lead", "Bilal", "Might be interested down the line, can you tell me more about what you offer?")

# Test 5: Empty message (edge case)
run_test("Test 5: Empty message", "Hina", "")

# Test 6: Long/detailed message (edge case)
run_test(
    "Test 6: Long detailed message",
    "Kamran",
    "We're a 50-person company looking to switch vendors urgently, need pricing "
    "for enterprise tier, want to sign this week if the numbers work, please "
    "call me ASAP at your earliest convenience.",
)