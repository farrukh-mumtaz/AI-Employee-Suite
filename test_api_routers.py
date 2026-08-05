from backend.app.api.sales import send_sales_message
from backend.app.api.marketing import generate_marketing_content
from backend.app.schemas.sales import SalesAgentRequest
from backend.app.schemas.marketing import MarketingAgentRequest


print("=== Sales Agent router: hot lead ===")
sales_result = send_sales_message(
    SalesAgentRequest(user_input="I'm interested in your pricing, want to sign up this week", lead_name="Ali")
)
print(sales_result)
print()

print("=== Marketing Agent router: content generation ===")
marketing_result = generate_marketing_content(
    MarketingAgentRequest(workflow="content", content_topic="new product launch", platform="instagram", tone="friendly")
)
print(marketing_result)

print("=== Sales Agent router: lead with objection ===")
objection_result = send_sales_message(
    SalesAgentRequest(user_input="Interested but this seems way too expensive compared to competitors", lead_name="Sara")
)
print(objection_result)


from backend.app.agents.sales_agent.graph import build_sales_graph

print("=== Direct graph invoke (bypassing router) - same objection input ===")
direct_graph = build_sales_graph()
direct_result = direct_graph.invoke({
    "messages": [], "user_input": "Interested but this seems way too expensive compared to competitors",
    "agent_response": None, "agent_name": "sales_agent",
    "system_prompt": "You are a sales assistant for a company.",
    "intent": None, "lead_name": "Sara", "notified": None,
    "followup_email_subject": None, "followup_email_body": None,
    "has_objection": None, "objection_response": None,
})
print("=== Sales Agent router: lead with objection (NOTE: objection handling not yet on main - see PR #4) ===")
objection_result = send_sales_message(
    SalesAgentRequest(user_input="Interested but this seems way too expensive compared to competitors", lead_name="Sara")
)
print(objection_result)
print("(has_objection will be None until PR #4 merges into main - this is expected, not a bug)")