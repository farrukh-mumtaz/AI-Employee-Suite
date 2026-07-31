from backend.app.agents.sales_agent.nodes import handle_objection_node


def run_test(label, name, message):
    print(f"=== {label} ===")
    state = {
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
        "has_objection": None,
        "objection_response": None,
    }
    result = handle_objection_node(state)
    print("Has objection:", result.get("has_objection"))
    print("Response:", result.get("objection_response"))
    print()


# Clear objection: price concern
run_test("Test 1: Price objection", "Ali", "This seems way too expensive for what we need")

# Clear objection: already using a competitor
run_test("Test 2: Competitor objection", "Sara", "We're already using a different tool and it works fine")

# NOT an objection - just a question
run_test("Test 3: Not an objection", "Bilal", "Sounds good, can you tell me more about the enterprise plan?")