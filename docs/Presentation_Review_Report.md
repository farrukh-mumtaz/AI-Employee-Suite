# Presentation Review Report — HR & Support Agents

## Purpose

Before HR/Support Agent material is presented (demo, stakeholder review, or
onboarding a new contributor), this report verifies the technical accuracy
of the existing written documentation and code comments against the actual
source code and a live test run. It lists what was verified as accurate,
what inconsistencies were found, and what correction each one needs.

**Method:** Every claim below was checked by reading the actual source file
it describes (not by re-reading other documentation) and, where testable, by
running the test suite directly. Date of this review: **2026-08-07**. Branch
reviewed: `samia-hr-agent`.

---

## 1. Verified Accurate

The following claims, made across `HR_AGENT.md`, `SUPPORT_AGENT.md`,
`ORCHESTRATOR.md`, and `RAG_DESIGN.md`, were checked against source and
confirmed **correct**:

| Claim | Verified against | Result |
|---|---|---|
| HR graph shape (`classify_intent` → onboarding/leave/unknown branches) | `hr_agent/graph.py` | ✅ Matches exactly |
| Support graph shape (`ticket_intake` → `ticket_classification` → `classify_intent` → 4 branches) | `support_agent/graph.py` | ✅ Matches exactly |
| Orchestrator defaults to `"support"` on ambiguous input | `core/orchestrator.py` | ✅ Matches, and the code comment's stated rationale (every Support request creates a ticket) is accurate |
| Ticket-category confidence threshold is `0.6` | `support_agent/nodes.py`, `_TICKET_CATEGORY_CONFIDENCE_THRESHOLD` | ✅ Matches |
| `leave_reason` is informational only, not a gating input to auto-approval | `evaluate_leave_request_node` (`hr_agent/nodes.py`) — checks only `leave_type`/dates | ✅ Matches |
| Support's refund policy retrieval uses the real pgvector pipeline; HR's leave policy retrieval does not | `support_agent/nodes.py` (`rag_retrieval_node`) vs. `hr_agent/rag.py` (hardcoded list) | ✅ Matches — see §3.3 for a presentation risk this creates |
| Only HR sample documents have been ingested into the vector store | `ingest_docs.py` — 5 hardcoded HR strings, `source="hr_policy_sample"` | ✅ Matches |
| HR + Support + Orchestrator + cross-agent + retrieval suite: 205 tests passing | Full suite run during this review | ✅ `205 passed, 3 warnings, 53 subtests passed` |
| HR suite: 95 tests | `pytest` run on the 6 documented HR test files | ✅ `95 passed` |
| Support suite: 79 tests (sum of the 6-file table in `SUPPORT_AGENT.md` §9) | `pytest` run on the 6 documented Support test files | ✅ `79 passed` — table sum (5+13+4+35+10+12) matches exactly |
| Orchestrator suite: 14 tests | `pytest test_orchestrator_routing.py` | ✅ `14 passed` |
| Cross-agent routing suite: 6 tests | `pytest test_cross_agent_routing.py` | ✅ `6 passed` |
| `main.py` still uses deprecated `@app.on_event("startup")` | `backend/app/main.py` line 13, plus live `DeprecationWarning` in every test run | ✅ Confirmed, already flagged in `HR_AGENT.md` §11 |
| `requirements.txt` omits `langgraph`, `langchain-groq`, `pytest`, `httpx` | Direct read of `requirements.txt` | ✅ Confirmed — also omits `pgvector`, which `models/document.py` imports directly |

---

## 2. Inconsistencies Found

### 2.1 `SUPPORT_AGENT.md` understates `test_retrieval.py`'s test count — **Low severity, factual error**

**Claim (SUPPORT_AGENT.md §9):** "`test_retrieval.py` (8 tests) for the shared `core/retrieval.py` dialect-routing fix."

**Actual:** `pytest test_retrieval.py --collect-only` lists **11** tests across 4 test classes (`CosineSimilarityTests` ×4, `RetrieveRelevantDocsSQLiteFallbackTests` ×3, `RetrieveRelevantDocsPostgresPathTests` ×1, `RetrieveRelevantDocsCachingTests` ×3), and the suite reports `11 passed`.

**Impact:** Low — doesn't affect functionality, but a presenter citing "8 tests" for this file would be corrected on the spot if anyone in the room ran the suite.

**Suggested correction:** Update `SUPPORT_AGENT.md` §9 to read "`test_retrieval.py` (11 tests)."

---

### 2.2 `testing_findings.md` describes leave-decision behavior that no longer matches the code — **Medium severity, stale documentation**

**Claim (`testing_findings.md`, "Expected Result" and "Actual Result" sections):** States that `leave_decision` is set to `"pending_manual_review"`, and explicitly frames this as permanent design: *"the agent never auto-approves/denies, per the placeholder design."*

**Actual (current code):**
- `backend/app/agents/hr_agent/state.py`: `LeaveDecision = Literal["approved", "rejected"]` — there is no `"pending_manual_review"` value in the type.
- `backend/app/agents/hr_agent/nodes.py`, `evaluate_leave_request_node`: sets `decision = "approved" if is_fully_specified else "rejected"` — a real binary auto-approval/manual-review decision based on extraction completeness, not a permanent "always manual" placeholder.
- Both `HR_AGENT.md` (current) and `SUPPORT_AGENT.md` (current) correctly describe this binary behavior for HR, and correctly describe the Support Agent's refund workflow (not the HR leave workflow) as the one that's *always* `"pending_manual_review"`.

**Impact:** Medium. `testing_findings.md` is a dated artifact from an earlier stage of the HR Agent's design (the leave workflow evidently used to always defer to manual review before the current type/date-driven auto-approval logic was added). If this file is pulled into presentation material as if it describes current behavior, it will directly contradict a live demo showing an auto-approved leave request.

**Suggested correction:** Either (a) add a dated note at the top of `testing_findings.md` stating it reflects a prior design and pointing readers to `HR_AGENT.md` §3 for current behavior, or (b) exclude this file from presentation source material entirely and cite `HR_AGENT.md` / `HR_AGENT_TEST_REPORT_LEAVE_AND_API.md` instead.

---

### 2.3 HR Agent documentation doesn't mention the DB-backed CRUD and Auth endpoints living under the same routers — **Medium severity, completeness gap**

**Observation:** `HR_AGENT.md` documents `POST /hr/message` as "the" HR Agent API surface (§5, "API Endpoints"). In the actual code, `backend/app/api/hr.py` also defines seven additional, JWT-authenticated endpoints (`/hr/employees` ×4, `/hr/leaves` ×3) backed by real `Employee`/`LeaveRequest` SQLModel tables — entirely separate from the LangGraph conversational agent. Similarly, `/auth/*` (signup/login/refresh/admin-only) exists and is registered in `main.py`, but isn't mentioned in any of `HR_AGENT.md`, `SUPPORT_AGENT.md`, or `ORCHESTRATOR.md`.

**Impact:** Medium for a presentation specifically — if a slide or demo script is built solely from `HR_AGENT.md`, it will present `/hr/message` as the entire HR surface and omit a materially different, already-working subsystem (authenticated employee/leave record-keeping) that a stakeholder may reasonably expect to see. This is not a code defect — the code is correct and tested — it's a gap in what's been written up.

**Suggested correction:** Covered in this documentation pass — see [HR_Support_Product_Documentation.md](HR_Support_Product_Documentation.md) §5.2–§5.3, which documents both endpoint groups and explicitly notes they are **not** wired together (a leave request submitted via `/hr/message` does not create a `LeaveRequest` row). Recommend the same clarification be added to `HR_AGENT.md` itself, or that `HR_AGENT.md`'s scope be explicitly narrowed to "the conversational agent only" in its title/overview.

---

### 2.4 Risk of conflating "RAG-powered" between the two agents — **Medium severity, presentation-framing risk, not a doc error**

**Observation:** No existing document actually states this incorrectly — `HR_AGENT.md` correctly calls `hr_agent/rag.py` a "placeholder policy-document retrieval," and `RAG_DESIGN.md` / `SUPPORT_AGENT.md` correctly describe the real pgvector pipeline. However, `RAG_DESIGN.md` is written in general terms ("Any agent (HR, Sales, etc.) can add `rag_retrieval_node` to their LangGraph flow") without stating that **HR does not currently do so** — the HR leave workflow uses its own, separate, keyword-only `rag.py`, not `core/rag_node.py`.

**Impact:** Medium, specifically for live presentation risk: if a presenter reads `RAG_DESIGN.md` in isolation and infers "the HR Agent uses this RAG pipeline," and then a technical audience member asks "is the leave policy context coming from the vector database?", the honest answer is no — it's a 4-string hardcoded list matched by keyword overlap. This is exactly the kind of claim that unravels credibility mid-demo if not preempted.

**Suggested correction:** Add one sentence to `RAG_DESIGN.md`'s "Notes" section stating explicitly which agents currently use the shared pipeline (Support's refund workflow) and which don't yet (HR's leave workflow, which has its own separate placeholder). Also reflected in [HR_Support_Product_Documentation.md](HR_Support_Product_Documentation.md) §10 ("Known Gaps") and the demo script's talking points.

---

## 3. Items Checked and Found *Already* Correctly Flagged (no action needed)

These are gaps in the *product*, not the documentation — the existing docs already disclose them accurately as placeholders/future work, so no correction is needed, but they are worth restating for anyone preparing presentation talking points so nothing is overstated live:

- Password reset, order-status lookup, and refund decisioning are all simulated — no real auth, order-management, or payments system is called.
- Extraction (name/role/dates/leave type/account email/order ID/refund reason) is regex/keyword-based, not an LLM structured-extraction step.
- No conversation memory/session persistence — every request is a stateless, independent graph run.
- No dedicated workflow exists for leave/refund *policy questions*, *balance checks*, or *status lookups on an existing request* — both agents correctly decline these to `unknown` rather than mishandling them (this was itself a bug fix — see `WEEKLY_TESTING_SUMMARY.md` bugs #1–#2 — and is now working as intended).

---

## 4. Summary of Corrections to Apply

| # | File | Correction | Priority |
|---|---|---|---|
| 1 | `SUPPORT_AGENT.md` §9 | Change "`test_retrieval.py` (8 tests)" → "(11 tests)" | Low |
| 2 | `testing_findings.md` | Add a dated note that this reflects a prior design, or exclude from presentation source material | Medium |
| 3 | `HR_AGENT.md` | Note that `/hr` also hosts unrelated, JWT-authenticated Employee/LeaveRequest CRUD endpoints not wired to the conversational agent | Medium |
| 4 | `RAG_DESIGN.md` | State explicitly that HR's leave workflow does not yet use the shared RAG pipeline described in this document | Medium |

None of the four corrections above require a code change — all are documentation-only fixes. No inconsistency was found between the code and its *own* module-level documentation (`HR_AGENT.md`'s core workflow/graph/API claims, `SUPPORT_AGENT.md`'s core workflow/graph/API claims, and `ORCHESTRATOR.md`'s integration claims all checked out against source).
