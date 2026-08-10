# Prompt Library — HR & Support Agents

This document catalogs every LLM prompt template actually defined in the
codebase for the HR Agent, the Support Agent, and the Orchestrator that
routes between them. All prompt text below is copied verbatim from source —
nothing has been paraphrased or invented.

**Sources:**
- `backend/app/agents/hr_agent/prompts.py`
- `backend/app/agents/support_agent/prompts.py`
- `backend/app/core/orchestrator.py` (`ROUTE_AGENT_PROMPT`)

**Model:** All prompts are sent to Groq's `llama-3.3-70b-versatile` via
`langchain_groq.ChatGroq`, configured once in `backend/app/core/llm_client.py`
with `temperature=0.3`. There is no per-prompt model or temperature override
— every prompt in this library shares the same model configuration.

**Shared failure behavior:** Every prompt below is invoked through a local
`_invoke_llm(prompt, fallback=...)` helper (defined separately in
`hr_agent/nodes.py` and `support_agent/nodes.py`, and inline in
`orchestrator.py`). If the LLM call raises an exception or returns an empty
response, the node uses a deterministic fallback string instead of crashing.
Fallback text is noted per-prompt below where one exists.

---

## Table of Contents

1. [HR Agent Prompts](#hr-agent-prompts)
   - [1.1 CLASSIFY_INTENT_PROMPT (HR)](#11-classify_intent_prompt-hr)
   - [1.2 ONBOARDING_WELCOME_PROMPT](#12-onboarding_welcome_prompt)
   - [1.3 LEAVE_REQUEST_APPROVED_PROMPT](#13-leave_request_approved_prompt)
   - [1.4 LEAVE_REQUEST_REJECTED_PROMPT](#14-leave_request_rejected_prompt)
   - [1.5 ONBOARDING_CHECKLIST_TEMPLATE (non-LLM)](#15-onboarding_checklist_template-non-llm)
2. [Support Agent Prompts](#support-agent-prompts)
   - [2.1 TICKET_CLASSIFICATION_PROMPT](#21-ticket_classification_prompt)
   - [2.2 CLASSIFY_INTENT_PROMPT (Support)](#22-classify_intent_prompt-support)
   - [2.3 PASSWORD_RESET_PROMPT](#23-password_reset_prompt)
   - [2.4 ORDER_STATUS_PROMPT](#24-order_status_prompt)
   - [2.5 REFUND_REQUEST_PROMPT](#25-refund_request_prompt)
3. [Orchestrator Prompt](#orchestrator-prompt)
   - [3.1 ROUTE_AGENT_PROMPT](#31-route_agent_prompt)

---

## HR Agent Prompts

### 1.1 CLASSIFY_INTENT_PROMPT (HR)

**Purpose:** Entry-point intent router for the HR Agent graph. Decides whether
an incoming free-text message is a new-hire onboarding request, a new leave
submission, or neither. Its output drives the `_route_by_workflow` conditional
edge in `backend/app/agents/hr_agent/graph.py`.

**Node:** `classify_intent_node` (`backend/app/agents/hr_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are an intent classifier for an HR assistant.
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
```

**Inputs:** `user_input` (string) — the raw free-text message. If empty/whitespace-only, the node short-circuits and returns `"unknown"` without calling the LLM at all.

**Outputs:** A single lowercase word: `onboarding`, `leave_request`, or `unknown` (any other reply is coerced to `unknown`), stored as `state["workflow"]`.

**Fallback on LLM failure:** `"unknown"`.

**Examples:**

| Input | Expected classification |
|---|---|
| "Please onboard John Doe as a Backend Engineer starting next week" | `onboarding` |
| "Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure." | `leave_request` |
| "What's the parental leave policy?" | `unknown` (policy question, not a submission) |
| "How many vacation days do I have left?" | `unknown` (balance inquiry) |
| "What is the weather like today?" | `unknown` |

> This prompt's wording was tightened during testing (see `WEEKLY_TESTING_SUMMARY.md`, bug #1) after policy/balance questions were found to be misclassified as `leave_request`, producing a misleading "your request needs manual review" response for a request the user never made.

---

### 1.2 ONBOARDING_WELCOME_PROMPT

**Purpose:** Drafts the customer-facing welcome message for a new hire once employee details have been extracted from the incoming message.

**Node:** `generate_welcome_message_node` (`backend/app/agents/hr_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the HR Agent welcoming a new employee.
Write a short, friendly welcome message (3-5 sentences) for the following
new hire. Mention their role and that HR will guide them through onboarding.

Employee name: {employee_name}
Role: {employee_role}
Start date: {start_date}
```

**Inputs:** `employee_name`, `employee_role`, `start_date` — each defaults to `"Unknown"` if extraction (`extraction.py`) found nothing.

**Outputs:** Free-text welcome message (3–5 sentences), stored as `state["agent_response"]`.

**Fallback on LLM failure:**
```text
Welcome, {employee_name}! We're excited to have you join us{ as <role>, if known}. HR will be in touch shortly to guide you through onboarding.
```

**Example:**
- Input state: `employee_name="Jane Smith"`, `employee_role="Product Manager"`, `start_date="2026-08-15"`
- Example output: *"Welcome aboard, Jane! We're excited to have you join us as Product Manager. HR will reach out shortly to guide you through onboarding."*

---

### 1.3 LEAVE_REQUEST_APPROVED_PROMPT

**Purpose:** Drafts the confirmation message when `evaluate_leave_request_node` has determined a leave request is fully specified (auto-approved branch).

**Node:** `approve_leave_node` (`backend/app/agents/hr_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the HR Agent confirming an approved leave request.
Write a short, friendly confirmation (2-4 sentences) letting the employee
know their leave request has been approved. Mention the leave type and
dates, and acknowledge the reason if one was given. You may reference the
policy context below if it is relevant. No employee name is provided --
greet them generically (e.g. "Hi there") rather than inventing a
placeholder like "[Employee]" or "[Name]".

Leave type: {leave_type}
Start date: {leave_start_date}
End date: {leave_end_date}
Reason: {leave_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
```

**Inputs:** `leave_type`, `leave_start_date`, `leave_end_date`, `leave_reason` (from `extraction.py`); `policy_context` — newline-joined snippets from `retrieve_leave_policy` (`hr_agent/rag.py`); `user_input` — the original message.

**Outputs:** Free-text approval confirmation, stored as `state["agent_response"]`.

**Fallback on LLM failure:**
```text
Good news -- your {leave_type} request from {leave_start_date} to {leave_end_date} has been approved.
```

**Example:**
- Input: `leave_type="sick leave"`, `leave_start_date="Aug 1"`, `leave_end_date="Aug 3"`, `leave_reason="a medical procedure"`
- Example output: *"Your sick leave from Aug 1 to Aug 3 has been approved. Hope the procedure goes well!"*

> The explicit "do NOT invent a placeholder like `[Employee]`" instruction was added after live-model testing found the model sometimes greeted the user with a literal `"Dear [Employee],"` bracket (see `WEEKLY_TESTING_SUMMARY.md`, bug #3).

---

### 1.4 LEAVE_REQUEST_REJECTED_PROMPT

**Purpose:** Drafts the message when a leave request could **not** be fully extracted (missing/unclear type or dates) and is routed to manual HR review. This is a routing outcome, not a denial — the prompt explicitly instructs the model never to imply the request was denied.

**Node:** `reject_leave_node` (`backend/app/agents/hr_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the HR Agent responding to a leave request that could not be
automatically approved. Write a short, courteous message (2-4 sentences)
explaining that the request needs manual HR review -- for example because
some details were missing or unclear -- and that HR will follow up. Do NOT
imply the request has been denied. No employee name is provided -- greet
them generically (e.g. "Hi there") rather than inventing a placeholder like
"[Employee]" or "[Name]".

Leave type: {leave_type}
Start date: {leave_start_date}
End date: {leave_end_date}
Reason: {leave_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
```

**Inputs:** Same shape as §1.3 (leave fields default to `"Unspecified"` / `"Not specified"` when missing).

**Outputs:** Free-text manual-review message, stored as `state["agent_response"]`.

**Fallback on LLM failure:**
```text
We weren't able to automatically process your leave request because some details were missing or unclear. It has been forwarded to HR for manual review.
```

**Example:**
- Input: `"I need to request leave, not sure of the dates yet."` → `leave_type`/dates fall back to `"Unspecified"` → decision `"rejected"` (manual review) → the model drafts a courteous "we'll need a bit more information, HR will follow up" style message.

---

### 1.5 ONBOARDING_CHECKLIST_TEMPLATE (non-LLM)

Not a prompt — a static Python list attached verbatim to every onboarding response by `generate_onboarding_checklist_node`. Included here for completeness since it is part of the onboarding "prompt-adjacent" content surfaced to the user:

```text
- Send offer letter and collect signed contract
- Provision company email and accounts
- Assign onboarding buddy / manager
- Schedule first-day orientation
- Collect tax and payroll documentation
- Set up workstation / equipment
```

There is no personalization by role or department today; the source code marks this as a placeholder pending real HRIS integration.

---

## Support Agent Prompts

### 2.1 TICKET_CLASSIFICATION_PROMPT

**Purpose:** Assigns every support ticket a business/reporting category with a confidence score, **independent** of which workflow branch ends up handling it. Runs before intent routing on every request.

**Node:** `ticket_classification_node` (`backend/app/agents/support_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are a ticket classification system for customer support.
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
{"category": "<one of the categories above>", "confidence": <float between 0.0 and 1.0>}

User message:
{user_input}
```

**Inputs:** `user_input`. Empty/whitespace input short-circuits to `("Unknown", 0.0)` without calling the LLM.

**Outputs:** Strict JSON `{"category": ..., "confidence": ...}`, parsed into `state["ticket_category"]` / `state["ticket_category_confidence"]`. If the category isn't one of the 7 recognized labels, or confidence is below `0.6`, the category is downgraded to `"Unknown"`.

**Fallback on LLM/parse failure:** `("Unknown", 0.0)`.

**Example:**
- Input: `"I'd like a refund for order #4521, it arrived broken."`
- Example output: `{"category": "Refund", "confidence": 0.93}`

---

### 2.2 CLASSIFY_INTENT_PROMPT (Support)

**Purpose:** Entry-point-adjacent router that decides whether the request is a password reset, order-status check, or refund request. Its output drives the `_route_by_workflow` conditional edge in `backend/app/agents/support_agent/graph.py`.

**Node:** `classify_intent_node` (`backend/app/agents/support_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are an intent classifier for a customer support assistant.
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
```

**Inputs:** `user_input`. Empty/whitespace input short-circuits to `"unknown"` without an LLM call.

**Outputs:** One lowercase word: `password_reset`, `order_status`, `refund_request`, or `unknown` (anything else coerced to `unknown`), stored as `state["workflow"]`.

**Fallback on LLM failure:** `"unknown"`.

**Examples:**

| Input | Expected classification |
|---|---|
| "I forgot my password and I'm locked out of my account." | `password_reset` |
| "I'd like a refund for order #4521, it arrived broken." | `refund_request` |
| "Just wondering what your return policy is." | `unknown` (policy question, not a request) |
| "I was charged twice for my subscription this month." | `unknown` (Billing has no dedicated workflow branch) |

> Like its HR counterpart, this prompt's wording was tightened to require an *actual* refund request on the customer's own order — see `WEEKLY_TESTING_SUMMARY.md`, bug #2, where general policy questions were previously misrouted into `refund_request`, creating a phantom `pending_manual_review` ticket.

---

### 2.3 PASSWORD_RESET_PROMPT

**Purpose:** Drafts the confirmation message after a (simulated) password reset link has been "sent."

**Node:** `send_password_reset_node` (`backend/app/agents/support_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the Support Agent helping a user reset their password.
Write a short, friendly response (2-4 sentences) confirming that a password
reset link has been sent to their account email, and remind them to check
their spam folder if it doesn't arrive shortly.

Account email: {account_email}
```

**Inputs:** `account_email` — defaults to `"Unknown"` (extraction is a placeholder; no real auth/session lookup is wired up).

**Outputs:** Free-text confirmation, stored as `state["agent_response"]`; `state["reset_link_sent"]` is also set to `True`.

**Fallback on LLM failure:**
```text
A password reset link has been sent to {account_email}. Please check your inbox (and spam folder) shortly.
```

**Example output:** *"A password reset link has been sent to your account email."*

---

### 2.4 ORDER_STATUS_PROMPT

**Purpose:** Drafts a response summarizing an order's status.

**Node:** `generate_order_status_response_node` (`backend/app/agents/support_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the Support Agent answering an order status question.
Write a short, friendly response (2-4 sentences) sharing the current status
of the order below. If the status is a placeholder, let the user know the
order details are still being looked up.

Order ID: {order_id}
Order status: {order_status}

User message:
{user_input}
```

**Inputs:** `order_id` (defaults to `"Unspecified"`); `order_status` — the fixed placeholder string returned by `rag.py`'s `lookup_order_status` (no real order-management system is wired up); `user_input`.

**Outputs:** Free-text status summary, stored as `state["agent_response"]`.

**Fallback on LLM failure:**
```text
Here's the latest on order {order_id}: {order_status}.
```

---

### 2.5 REFUND_REQUEST_PROMPT

**Purpose:** Drafts a response acknowledging a refund request. The model is explicitly instructed **never** to approve or deny the refund itself.

**Node:** `evaluate_refund_request_node` (`backend/app/agents/support_agent/nodes.py`)

**System Prompt (verbatim template):**
```text
You are the Support Agent processing a refund request.
Use the relevant policy context below (if any) to draft a short response to
the customer acknowledging their request. Do NOT approve or deny the refund
yourself -- clearly state that it has been submitted for manual review.

Order ID: {order_id}
Reason for refund: {refund_reason}

Relevant policy context:
{policy_context}

User message:
{user_input}
```

**Inputs:** `order_id`, `refund_reason` (placeholder extraction, defaults to `"Unspecified"`); `policy_context` — real pgvector-retrieved policy text, read from `state["system_prompt"]` after `retrieve_refund_policy_node` runs (see [HR_Support_Product_Documentation.md](HR_Support_Product_Documentation.md) for the RAG pipeline); `user_input`.

**Outputs:** Free-text acknowledgement, stored as `state["agent_response"]`; `state["refund_decision"]` is always set to `"pending_manual_review"` (never auto-approved or auto-denied).

**Fallback on LLM failure:**
```text
Your refund request has been submitted for manual review. Our team will follow up with you shortly.
```

**Example output:** *"Your refund request has been submitted for manual review."*

---

## Orchestrator Prompt

### 3.1 ROUTE_AGENT_PROMPT

**Purpose:** The single classification call that decides whether an incoming message goes to the HR Agent's graph or the Support Agent's graph, when the caller doesn't already know which one applies. Used only by `POST /agent/message`; callers that already know which agent they need should call `/hr/message` or `/support/message` directly and never hit this prompt.

**Node:** `classify_target_agent_node` (`backend/app/core/orchestrator.py`)

**System Prompt (verbatim template):**
```text
You are a routing classifier for a company's internal AI assistants.
Read the user's message and decide which assistant should handle it.

Respond with exactly one word, lowercase, no punctuation:
- "hr" if the message is about employee onboarding, new hires, or an
  employee submitting a leave/time-off request.
- "support" if the message is about a customer support ticket: password
  resets, order status, refunds, or account issues.

User message:
{user_input}
```

**Inputs:** `user_input`. Empty input skips the LLM call entirely.

**Outputs:** `"hr"` or `"support"`, stored as `state["target_agent"]` and used by the `_route_by_target_agent` conditional edge.

**Fallback on LLM failure / unrecognized reply / empty input:** `"support"` — deliberately, not `"hr"`. The code comment in `orchestrator.py` explains why: every Support Agent request creates a ticket regardless of workflow outcome (via `ticket_intake`/`ticket_classification`), so an ambiguous message defaulting to Support is never silently dropped — it still lands in a ticket for manual follow-up. HR has no equivalent unconditional record-creation step.

**Examples:**

| Input | Routed to |
|---|---|
| "Please onboard John Doe as a Backend Engineer starting next week" | `hr` |
| "I forgot my password and I'm locked out of my account." | `support` |
| "" (empty) | `support` (default, no LLM call made) |

---

## Notes on Prompt Design Conventions

- **Single-word classification prompts** (`CLASSIFY_INTENT_PROMPT` ×2, `ROUTE_AGENT_PROMPT`) all use the same contract: "respond with exactly one word, lowercase, no punctuation," with an explicit enumerated list of valid values and an unambiguous `unknown`/fallback catch-all. Any reply outside the enumerated set is coerced to the fallback in code, not re-prompted.
- **Structured-JSON prompts** (`TICKET_CLASSIFICATION_PROMPT`) are used only where a numeric confidence score must accompany a label — the bare-word convention can't carry that.
- **Response-drafting prompts** (welcome/approval/rejection/password-reset/order-status/refund) all specify a sentence-count range (e.g. "2-4 sentences") to keep generated text short and consistent, and all have a hand-written deterministic fallback string for LLM outages.
- **No prompt in this library references chat history** — every request is a single, stateless message (`messages: []` on every initial state); there is no multi-turn conversation memory today.
