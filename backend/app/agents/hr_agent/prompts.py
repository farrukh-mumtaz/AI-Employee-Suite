# Prompt templates for the HR Agent.
#
# Kept separate from nodes.py so prompt copy can be iterated on (or swapped
# for a prompt-management system / versioned prompt store) without touching
# graph wiring or node logic.

CLASSIFY_INTENT_PROMPT = """You are an intent classifier for an HR assistant.
Read the user's message and decide which HR workflow it belongs to.

Respond with exactly one word, lowercase, no punctuation:
- "onboarding" if the message is about onboarding a new employee, setting up
  a new hire, first-day preparation, etc.
- "leave_request" if the message is about requesting time off, sick leave,
  vacation, parental leave, or checking leave status.
- "unknown" if it does not clearly match either workflow.

User message:
{user_input}
"""

# --- Employee Onboarding prompts ---

ONBOARDING_WELCOME_PROMPT = """You are the HR Agent welcoming a new employee.
Write a short, friendly welcome message (3-5 sentences) for the following
new hire. Mention their role and that HR will guide them through onboarding.

Employee name: {employee_name}
Role: {employee_role}
Start date: {start_date}
"""

# TODO(future integration): replace this static template with a checklist
# generated from the company's actual onboarding system / HRIS once available.
ONBOARDING_CHECKLIST_TEMPLATE = [
    "Send offer letter and collect signed contract",
    "Provision company email and accounts",
    "Assign onboarding buddy / manager",
    "Schedule first-day orientation",
    "Collect tax and payroll documentation",
    "Set up workstation / equipment",
]

# --- Leave Request prompts ---

LEAVE_REQUEST_EVALUATION_PROMPT = """You are the HR Agent processing a leave request.
Use the relevant policy context below (if any) to draft a short response to
the employee acknowledging their request. Do NOT approve or deny the request
yourself -- clearly state that it has been submitted for manual HR review.

Leave type: {leave_type}
Start date: {leave_start_date}
End date: {leave_end_date}

Relevant policy context:
{policy_context}

User message:
{user_input}
"""
