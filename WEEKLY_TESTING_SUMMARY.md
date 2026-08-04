# Weekly Testing Summary — HR Agent & Support Agent

**Week of:** 2026-07-28 to 2026-08-04
**Scope:** `backend/app/agents/hr_agent/`, `backend/app/agents/support_agent/`,
and their API/schema layers (`backend/app/api/`, `backend/app/schemas/`).
**Author:** Automated testing/fix pass (this session).

## 1. Summary

Both agents were already covered by a substantial pre-existing test suite
(152 tests, all passing) and prior test reports had found no defects in
production code. This round took a different approach: rather than
re-testing existing behavior, both agents were run against the **real Groq
LLM** with realistic and cross-domain input, and the actual output was read
for correctness rather than just checked for a well-formed response. That
surfaced two real, reproducible accuracy bugs (not caught by any
FakeLLM-based test, since a FakeLLM only ever does what the test author
told it to) plus a reliability gap and a missing capability found through
code/test-coverage comparison between the two agents. All are fixed, tested
(both deterministically and against the live model), and documented below.

## 2. Bugs Found and Fixed

| # | Agent | Bug | Severity | Fix |
|---|---|---|---|---|
| 1 | HR | `CLASSIFY_INTENT_PROMPT` routed leave **policy questions** ("what's our policy on parental leave?") and **balance inquiries** ("how many vacation days do I have left?") into the `leave_request` submission workflow, which can only evaluate a *new* request — producing a misleading "your leave request needs manual review" response for a request the user never made. | High (incorrect, confusing user-facing response) | Tightened the prompt: `leave_request` now requires an actual new time-off submission; policy/balance/status questions route to `unknown`. Verified against the real LLM. |
| 2 | Support | Same root cause as #1: `CLASSIFY_INTENT_PROMPT` routed a general policy question ("just wondering what your return policy is") into `refund_request`, silently creating a ticket with `refund_decision="pending_manual_review"` for a refund nobody asked for. | High (phantom transactional record + misleading response) | Tightened the prompt: `refund_request` now requires the customer to be actively asking for a refund on their own purchase. Verified against the real LLM. |
| 3 | HR | `LEAVE_REQUEST_REJECTED_PROMPT`/`APPROVED_PROMPT` gave the LLM no employee name, so it sometimes greeted the user with a literal `"Dear [Employee],"` placeholder bracket — confirmed live, twice. | Medium (unprofessional output) | Added an explicit instruction not to invent a placeholder; greet generically instead. |
| 4 | Support | Every LLM-calling node except `ticket_classification_node` called `llm.invoke()` directly with no error handling — a transient Groq failure (network error, rate limit, provider outage) would crash the entire graph invocation. HR Agent already centralizes this via `_invoke_llm()` with a deterministic fallback; Support had zero equivalent test coverage (`RaisingLLM`-style tests: HR had 4, Support had 0). | High (single point of failure, no graceful degradation) | Added the same `_invoke_llm()` pattern to every LLM-calling Support node. |
| 5 | Support | `generate_order_status_response_node` and `evaluate_refund_request_node` indexed `state["user_input"]` directly instead of `.get(...)` — a latent `KeyError` risk if that key were ever absent when those branches ran. | Low (defensive-coding gap, not yet observed in production) | Switched to `.get("user_input", "")`, matching every other node. |
| 6 | Support | `classify_intent_node` didn't short-circuit on empty input (HR's does) — wasted an LLM call and was inconsistent between the two agents. | Low | Added the same empty-input short-circuit as HR. |
| 7 | Support | No HTTP endpoint existed (`api/support.py` was missing, not registered in `main.py`) — already flagged in `SUPPORT_AGENT.md`'s "Future Improvements." This blocked realistic HTTP-level cross-testing against HR's `/hr/message` and left the Support Agent unusable by any real client. | Medium (missing capability) | Added `backend/app/api/support.py` + `backend/app/schemas/support.py`, mirroring `api/hr.py` exactly, and registered the router in `main.py`. |

**Also fixed while touching the affected code** (no separate user-facing
symptom, found via code review): `SupportAgentState` was missing
`total=False` (HR's equivalent has it, by design, since every field is
filled in progressively by nodes); extraction nodes (`extract_account_details_node`,
`extract_order_details_node`, `extract_refund_details_node`) used
`state.setdefault(...)`, which only checks *key presence* — an existing but
empty value (e.g. `account_email: ""`) would have been left as-is instead of
refilled, unlike HR's equivalent nodes. Both switched to match HR's
convention.

## 3. Accuracy Improvements

- **Intent-classification precision** (HR + Support): both agents' primary
  intent classifiers now correctly distinguish an actual transactional
  request from a question that merely mentions the same topic. This was
  verified against the real Groq model, not just a deterministic stub — see
  `test_live_llm_accuracy.py`.
- **Response professionalism** (HR): removed the placeholder-bracket
  failure mode from the leave-request approval/rejection messages.
- **Fallback message accuracy** (HR + Support): both agents' `unknown`
  clarification message now accurately describes what the agent can and
  can't do (previously implied the agent could handle *any* leave/refund-
  related message, including questions and status checks it actually
  cannot).
- **Reliability parity**: Support Agent now degrades gracefully on LLM
  failure exactly like the HR Agent, instead of crashing the whole request.

## 4. Test Scenarios Executed

**Live-LLM probe (pre-fix, real Groq model, no mocking)** — 10 realistic HR
messages, 10 realistic Support messages, 3 Support-domain messages through
the HR graph, and 2 HR-domain messages through the Support graph. This is
what surfaced bugs #1 and #2 above; routing isolation between the two
agents was already solid (no leakage found in either direction).

**Regression + new automated coverage (deterministic, FakeLLM-based):**

| Test file | Scenario | Result |
|---|---|---|
| `test_hr_agent*.py` (6 files, pre-existing) | Onboarding, leave request (approved/manual-review), unknown fallback, extraction heuristics, node contracts, API contract | 95/95 pass |
| `test_support_agent_graph.py`, `_nodes.py`, `_comprehensive.py`, `_sample_tickets.py` (pre-existing) | Password reset / order status / refund workflows, 25 realistic sample tickets across all 7 ticket categories, invalid/empty/unicode input, state isolation | 57/57 pass |
| `test_support_agent_api.py` (**new**) | `/support/message` HTTP contract: happy path (all 3 workflows + unknown), Pydantic validation (empty/missing/wrong-type/malformed body), graph-failure and empty-response 500 handling | 10/10 pass |
| `test_support_agent_resilience.py` (**new**) | LLM-failure fallback for every LLM-calling Support node; empty-LLM-response fallback; extraction nodes' "don't overwrite an existing field" contract | 12/12 pass |
| `test_cross_agent_routing.py` (**new**) | Support-domain input through the HR graph *and* API; HR-domain input through the Support graph *and* API; confirms neither agent's state fields leak into the other's result | 6/6 pass |
| `test_live_llm_accuracy.py` (**new**, opt-in, requires `GROQ_API_KEY`) | Real-Groq regression lock-in for bugs #1/#2: policy/balance questions vs. genuine requests, for both agents, plus live cross-agent routing isolation | 9/9 pass |

## 5. Test Results

```
python -m pytest test_hr_agent.py test_hr_agent_extraction.py test_hr_agent_nodes.py \
    test_hr_agent_graph.py test_hr_agent_comprehensive.py test_hr_agent_api.py \
    test_support_agent_comprehensive.py test_support_agent_graph.py test_support_agent_nodes.py \
    test_support_agent_sample_tickets.py test_support_agent_api.py test_support_agent_resilience.py \
    test_cross_agent_routing.py -q

180 passed, 53 subtests passed in ~9-17s   (deterministic, no network/GROQ_API_KEY required)

python -m pytest test_live_llm_accuracy.py -v

9 passed in ~16s   (live Groq model, requires GROQ_API_KEY; auto-skips otherwise)
```

**189 total HR + Support Agent tests** (152 pre-existing/updated + 28 new
deterministic + 9 new live-LLM), all passing. No regressions in the
unrelated Sales/Marketing agent modules (spot-checked; those files have no
pytest-collectible tests of their own).

## 6. Remaining Issues / Known Limitations

Not fixed in this pass — intentionally out of scope (would require new
workflow branches, not bug fixes) and now explicitly documented in both
`HR_AGENT.md` and `SUPPORT_AGENT.md`'s "Known Limitations" sections:

- **No dedicated workflow for leave/refund policy questions, balance
  checks, or status lookups on an existing request.** Both agents now
  correctly decline these (routing to `unknown` with an honest "please
  contact HR/support directly" message) rather than mishandling them, but
  neither can actually answer them yet. Flagged as a "Future Improvements"
  item in both docs (a read-only FAQ workflow grounded in the existing RAG
  pipeline would close this).
- **Extraction remains regex/keyword-based** (HR: name/role/date/leave-type;
  Support: account email/order ID/refund reason) — pre-existing, documented
  placeholder behavior, not a new defect from this pass.
- **Support Agent's refund-policy RAG pipeline** requires a real
  Postgres+pgvector database; this environment's `DATABASE_URL` is SQLite,
  so retrieval always hits its (already-tested) graceful-degradation path
  locally. Not a code defect — an environment/deployment prerequisite,
  documented in `SUPPORT_AGENT.md`.
- **`main.py` still uses the deprecated `@app.on_event("startup")`** —
  pre-existing `DeprecationWarning`, unrelated to this pass, left as-is per
  scope.
