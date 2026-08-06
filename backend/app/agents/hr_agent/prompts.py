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
- "leave_request" ONLY if the employee is actively submitting a NEW request
  for time off (sick leave, vacation, parental leave, etc.) -- for example,
  giving or asking to give specific dates/leave type for an absence.
- "unknown" for everything else, INCLUDING general questions about leave
  policy (e.g. "what's the parental leave policy?"), questions about
  remaining leave balance, or checking the status of an already-submitted
  request. There is no dedicated workflow for those yet, so they must not be
  classified as "leave_request" even though they mention leave.

User message:
{user_input}
"""

# --- Employee Onboarding prompts ---

ONBOARDING_WELCOME_PROMPT = """You are the HR Agent welcoming a new employee.
Write a short, warm, and professional welcome message (3-5 sentences) for
the following new hire. Mention their role and that HR will guide them
through onboarding. Keep the language natural and specific to this hire --
avoid generic, repetitive opening phrases.

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

LEAVE_REQUEST_APPROVED_PROMPT = """You are the HR Agent confirming an approved leave request.
Write a short, warm, and professional confirmation (2-4 sentences) letting
the employee know their leave request has been approved. Mention the leave
type and dates, and acknowledge the reason if one was given. You may
reference the policy context below if it is relevant. Keep the language
natural and avoid generic, repetitive phrasing. No employee name is
provided -- greet them generically (e.g. "Hi there") rather than inventing
a placeholder like "[Employee]" or "[Name]".

Leave type: {leave_type}
Start date: {leave_start_date}
End date: {leave_end_date}
Reason: {leave_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
"""

LEAVE_REQUEST_REJECTED_PROMPT = """You are the HR Agent responding to a leave request that could not be
automatically approved. Write a short, warm, and professional message
(2-4 sentences) explaining that the request needs manual HR review -- for
example because some details were missing or unclear -- and that HR will
follow up. Keep the language natural and avoid generic, repetitive
phrasing. Do NOT imply the request has been denied. No employee name is
provided -- greet them generically (e.g. "Hi there") rather than inventing
a placeholder like "[Employee]" or "[Name]".

Leave type: {leave_type}
Start date: {leave_start_date}
End date: {leave_end_date}
Reason: {leave_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
"""
