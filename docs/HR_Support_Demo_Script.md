# HR & Support Agents — 5-Minute Demo Script

## Purpose

A live-demo script for showing the HR Agent, Support Agent, and Orchestrator
working end-to-end. Every request/response pair below is either taken
directly from the verified examples in
[HR_Support_Product_Documentation.md](HR_Support_Product_Documentation.md) or
from a documented example in `HR_AGENT.md`/`SUPPORT_AGENT.md` — nothing here
is a hypothetical response the system hasn't actually been shown to produce.
Exact wording from a live LLM call may vary slightly each run (temperature
`0.3`); the *shape* and *fields* will not.

**Pre-requisites (set up before the audience arrives, not during the demo):**
- Backend running locally: `uvicorn backend.app.main:app --reload` (or the team's standard run command), reachable at `http://127.0.0.1:8000`.
- `GROQ_API_KEY` set in `.env` so live LLM calls succeed (a missing/invalid key still works — every node degrades to a deterministic fallback string — but live responses read more naturally).
- A terminal with `curl` ready, and `http://127.0.0.1:8000/docs` (FastAPI's auto-generated Swagger UI) open in a browser tab as a visual backup.
- Optional: a second terminal tailing backend logs, to show the graceful-fallback logging if you plan to demonstrate the LLM-failure path (§6, optional).

**Total runtime: ~5 minutes.** Timings below are per-segment targets, not hard stops — talk to the room's energy, not the clock.

---

## Segment 1 — Framing (0:00–0:30, 30s)

**Narration:**
> "The AI Employee Suite backend currently ships two working conversational agents — HR and Support — plus an Orchestrator that routes between them without the caller needing to know which one applies in advance. Everything I'm about to show is a real HTTP call against the actual FastAPI backend, not a mockup. Both agents are built on LangGraph, and both fall back gracefully to a deterministic response if the LLM call itself fails — I'll touch on that at the end."

**Screen action:** Show the terminal and the `/docs` tab side by side. No commands run yet.

---

## Segment 2 — HR Agent: Onboarding (0:30–1:30, 60s)

**Narration:**
> "First, the HR Agent. It's one endpoint, `POST /hr/message` — you send it free text, and it figures out whether you're onboarding someone or requesting leave. Let's onboard a new hire."

**Screen action — run:**
```bash
curl -X POST http://127.0.0.1:8000/hr/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "New hire, Jane Smith, joining as a Product Manager starting 2026-08-15."}'
```

**Expected response (documented example, `HR_Support_Product_Documentation.md` §7):**
```json
{
  "agent_response": "Welcome aboard, Jane! We're excited to have you join us as Product Manager. HR will reach out shortly to guide you through onboarding.",
  "workflow": "onboarding",
  "employee_name": "Jane Smith",
  "employee_role": "Product Manager",
  "start_date": "2026-08-15",
  "onboarding_checklist": [
    "Send offer letter and collect signed contract",
    "Provision company email and accounts",
    "Assign onboarding buddy / manager",
    "Schedule first-day orientation",
    "Collect tax and payroll documentation",
    "Set up workstation / equipment"
  ]
}
```

**Narration (while response is on screen):**
> "Three things happened in one call: it classified this as onboarding, it pulled the name, role, and start date straight out of the sentence with no structured form, and it attached a standard onboarding checklist. That extraction is regex-based today, not an LLM call — worth knowing if someone asks how it scales to unusual phrasing."

---

## Segment 3 — HR Agent: Leave Request, Auto-Approved (1:30–2:15, 45s)

**Narration:**
> "Same endpoint, different intent — a leave request."

**Screen action — run:**
```bash
curl -X POST http://127.0.0.1:8000/hr/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Requesting sick leave from Aug 1 to Aug 3 because of a medical procedure."}'
```

**Expected response (documented example):**
```json
{
  "agent_response": "Your sick leave from Aug 1 to Aug 3 has been approved. Hope the procedure goes well!",
  "workflow": "leave_request",
  "leave_type": "sick leave",
  "leave_start_date": "Aug 1",
  "leave_end_date": "Aug 3",
  "leave_reason": "a medical procedure",
  "leave_decision": "approved"
}
```

**Narration:**
> "It extracted leave type, both dates, and the reason, checked those against a policy snippet lookup, and auto-approved — because everything it needed was present and unambiguous. If any of type or dates had come back empty, this would route to manual HR review instead, with a message that's carefully worded to never sound like a denial."

**(Optional, if time allows) — show the manual-review path:**
```bash
curl -X POST http://127.0.0.1:8000/hr/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I need to request leave, not sure of the dates yet."}'
```
This returns `"leave_decision": "rejected"` (a routing label meaning *manual review*, not a denial) with a courteous message explaining HR will follow up.

---

## Segment 4 — Support Agent: Refund + Ticket Classification (2:15–3:15, 60s)

**Narration:**
> "Now the Support Agent — same pattern, `POST /support/message`. Every single message it receives gets a support ticket immediately, before any classification happens, so nothing falls through the cracks even if the request turns out to be off-topic."

**Screen action — run:**
```bash
curl -X POST http://127.0.0.1:8000/support/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I'\''d like a refund for order #4521, it arrived broken."}'
```

**Expected response (documented example, abridged):**
```json
{
  "agent_response": "Your refund request has been submitted for manual review.",
  "workflow": "refund_request",
  "ticket_id": "TCK-4F2A9B10",
  "ticket_status": "Open",
  "ticket_category": "Refund",
  "ticket_category_confidence": 0.93,
  "refund_decision": "pending_manual_review"
}
```

**Narration:**
> "Notice two separate classification results here: `ticket_category` — that's a business/reporting tag, running independently for every ticket — and `workflow`, which is what actually decided which branch of the graph to run. They're deliberately decoupled. And the refund policy context this drafted from isn't the model's general knowledge — it's retrieved from a real vector database over the company's actual policy documents using pgvector similarity search. The agent never approves or denies a refund itself; it always routes to manual review by design."

**(Optional) — show a category with no dedicated workflow, proving the independence claim:**
```bash
curl -X POST http://127.0.0.1:8000/support/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I was charged twice for my subscription this month."}'
```
Returns `"ticket_category": "Billing"` but `"workflow": "unknown"` — a real ticket still gets created and categorized correctly for reporting, even though there's no automated Billing workflow yet.

---

## Segment 5 — Orchestrator: One Endpoint, Either Agent (3:15–4:15, 60s)

**Narration:**
> "Everything so far assumed the caller already knew which agent to talk to. The Orchestrator removes that assumption — one endpoint, `POST /agent/message`, and it decides for you."

**Screen action — run (HR-domain input through the single entry point):**
```bash
curl -X POST http://127.0.0.1:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Please onboard John Doe as a Backend Engineer starting next week"}'
```

**Expected response shape:**
```json
{
  "agent": "hr",
  "hr": {
    "agent_response": "...",
    "workflow": "onboarding",
    "employee_name": "John Doe",
    "employee_role": "Backend Engineer"
  },
  "support": null
}
```

**Screen action — run (Support-domain input, same endpoint):**
```bash
curl -X POST http://127.0.0.1:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"user_input": "I forgot my password and I'\''m locked out of my account."}'
```

**Narration:**
> "Same endpoint, correctly routed to Support this time, `reset_link_sent: true`, `agent: support`. Under the hood the Orchestrator doesn't reimplement any of the logic I just showed you — it invokes the exact same compiled HR and Support graphs, unmodified. And if a message is genuinely ambiguous or the classifier call fails, it defaults to Support rather than HR — deliberately, because every Support request creates a ticket regardless of outcome, so an uncertain message never gets silently dropped."

---

## Segment 6 — Closing: Reliability, Honestly Scoped (4:15–5:00, 45s)

**Narration:**
> "Two things worth being upfront about before questions. First: every LLM call in both agents is wrapped so a Groq outage or rate limit degrades to a deterministic fallback message instead of crashing the request — I can demo that live if useful, it just means unplugging the API key. Second: this is a scaffold, not a finished product — password reset, order lookup, and refund approval are all simulated today, and the HR leave-policy retrieval is a small hardcoded keyword list, not the same real vector-search pipeline the Support refund workflow uses. All of that is documented, not hidden, and it's exactly the roadmap for what gets wired up next."

**Screen action:** Switch to `/docs` (Swagger UI) briefly to show the full endpoint list as a closing visual, then stop sharing.

**(Optional, if a technical audience and time remains) — LLM-failure fallback demo:**
Temporarily unset/rename `GROQ_API_KEY` in `.env`, restart the server, and re-run the Segment 2 onboarding request. The response still returns `200` with a fallback welcome message (e.g. *"Welcome, Jane! We're excited to have you join us as Product Manager. HR will be in touch shortly to guide you through onboarding."*) instead of an error — demonstrating the `_invoke_llm()` graceful-degradation pattern used by every LLM-calling node in both agents.

---

## Quick-Reference Timing Table

| Segment | Content | Target time | Cumulative |
|---|---|---|---|
| 1 | Framing | 0:30 | 0:30 |
| 2 | HR — Onboarding | 1:00 | 1:30 |
| 3 | HR — Leave request (auto-approved) | 0:45 | 2:15 |
| 4 | Support — Refund + ticket classification | 1:00 | 3:15 |
| 5 | Orchestrator — single entry point | 1:00 | 4:15 |
| 6 | Closing — reliability & honest scoping | 0:45 | 5:00 |

## Fallback Plan If Live Calls Fail

If network/Groq access is unreliable during the live demo, every response
shown above is copied verbatim from documented, previously-verified example
output (`HR_Support_Product_Documentation.md` §7). Narrate from the JSON in
this script directly rather than the terminal — the content shown will still
be accurate to what the system produces, just not captured live.
