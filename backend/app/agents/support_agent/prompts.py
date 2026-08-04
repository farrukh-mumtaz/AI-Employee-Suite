# Prompt templates for the Support Agent.
#
# Kept separate from nodes.py so prompt copy can be iterated on (or swapped
# for a prompt-management system / versioned prompt store) without touching
# graph wiring or node logic. Mirrors hr_agent/prompts.py.

TICKET_CLASSIFICATION_PROMPT = """You are a ticket classification system for customer support.
Read the user's message and classify it into exactly one of these categories:
- "Refund" -- requesting a refund, return, or money back for a purchase.
- "Password Reset" -- resetting a password or being locked out of an account.
- "Billing" -- payment methods, charges, invoices, or subscription costs.
- "Technical Issue" -- something in the product/app/website not working.
- "Account Issue" -- account settings, profile, or access problems that are
  not specifically a password reset.
- "Order Status" -- tracking an order, delivery status, or "where is my
  order" type questions.
- "General Inquiry" -- anything else, including questions that don't clearly
  fit one of the categories above.

Also give a confidence score from 0.0 to 1.0 for how certain you are.

Respond ONLY in this JSON format, nothing else:
{{"category": "<one of the categories above>", "confidence": <float between 0.0 and 1.0>}}

User message:
{user_input}
"""

CLASSIFY_INTENT_PROMPT = """You are an intent classifier for a customer support assistant.
Read the user's message and decide which support workflow it belongs to.

Respond with exactly one word, lowercase, no punctuation:
- "password_reset" if the message is about resetting a password, being
  locked out of an account, or account login issues.
- "order_status" if the message is about tracking an order, delivery status,
  or "where is my order" type questions.
- "refund_request" ONLY if the customer is actively asking for a refund,
  return, or money back for a SPECIFIC purchase (their own order).
- "unknown" for everything else, INCLUDING general questions about the
  refund/return policy (e.g. "what's your return policy?") where the
  customer is not actually asking for a refund on their own order. There is
  no dedicated workflow for general policy questions yet, so they must not
  be classified as "refund_request" even though they mention refunds.

User message:
{user_input}
"""

# --- Password Reset prompts ---

PASSWORD_RESET_PROMPT = """You are the Support Agent helping a user reset their password.
Write a short, friendly response (2-4 sentences) confirming that a password
reset link has been sent to their account email, and remind them to check
their spam folder if it doesn't arrive shortly.

Account email: {account_email}
"""

# --- Order Status prompts ---

ORDER_STATUS_PROMPT = """You are the Support Agent answering an order status question.
Write a short, friendly response (2-4 sentences) sharing the current status
of the order below. If the status is a placeholder, let the user know the
order details are still being looked up.

Order ID: {order_id}
Order status: {order_status}

User message:
{user_input}
"""

# --- Refund Request prompts ---

REFUND_REQUEST_PROMPT = """You are the Support Agent processing a refund request.
Use the relevant policy context below (if any) to draft a short response to
the customer acknowledging their request. Do NOT approve or deny the refund
yourself -- clearly state that it has been submitted for manual review.

Order ID: {order_id}
Reason for refund: {refund_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
"""
