# Support Agent — v1 Documentation

## 1. Overview

The Support Agent is a LangGraph-based conversational agent that automates
customer support intake and triage from a single free-text message:

- **Ticket intake** — every request immediately gets a ticket record (ID,
  status, priority, category placeholder), regardless of what it turns out
  to be about.
- **Ticket classification** — the ticket is classified into one of 7
  business/reporting categories with a confidence score, independent of
  which automated workflow (if any) ends up handling it.
- **Intent routing** — an LLM-based classifier decides whether the request
  is a **password reset**, **order status** check, or **refund request**,
  and routes to the matching workflow; anything else falls back to a
  clarification message.
- **Refund policy grounding** — the refund-request workflow retrieves
  relevant policy context from the company's real document store via the
  shared RAG (Retrieval-Augmented Generation) pipeline, instead of relying
  on the LLM's general knowledge.

Unlike the HR Agent, the Support Agent is **not yet exposed over HTTP** —
there is no `api/support.py` router registered in `backend/app/main.py`.
It's invoked directly by building the compiled graph and calling
`.invoke()`, exactly as the test suite does (see [Example
Requests](#10-example-requests)).

The agent's underlying LLM calls use Groq (`llama-3.3-70b-versatile`) via
`langchain_groq.ChatGroq`, configured once in
`backend/app/core/llm_client.py` — the same factory every agent in this repo
shares.

## 2. Architecture

The Support Agent is built on the same shared scaffold as every other agent
in this repo (see `backend/app/agents/hr_agent/` for the sibling
implementation), and reuses the shared RAG infrastructure rather than
maintaining its own:

```
backend/app/agents/support_agent/
    ├─ graph.py                  <- StateGraph wiring (nodes + conditional edges)
    ├─ nodes.py                  <- Node functions (business logic)
    ├─ state.py                  <- SupportAgentState (TypedDict)
    ├─ rag.py                    <- Order-status lookup (a transactional
    │                               lookup, not a RAG concern)
    └─ prompts.py                <- LLM prompt templates
    │
backend/app/core/
    ├─ state.py                  <- AgentState (base fields shared by all agents)
    ├─ graph.py                  <- Minimal single-node scaffold graph (not used directly)
    ├─ llm_client.py              <- get_llm() factory (Groq client)
    ├─ embeddings.py               <- BAAI/bge-m3 embedding model (sentence-transformers)
    ├─ retrieval.py                 <- pgvector cosine-distance document retrieval
    └─ rag_node.py                  <- rag_retrieval_node, the shared LangGraph RAG step
```

**Design principles carried through the implementation:**

- **Reuse the shared RAG pipeline, don't duplicate it** — refund-policy
  retrieval delegates to `core/rag_node.py`'s `rag_retrieval_node` (real
  pgvector semantic search), wrapped in try/except for graceful
  degradation. There is no agent-local keyword-matching retrieval anymore.
- **Ticket classification is independent of workflow routing** —
  `ticket_category`/`ticket_category_confidence` (business/reporting data)
  and `workflow` (which graph branch runs) are set by two separate nodes
  and never influence each other. Only 3 of the 7 ticket categories
  currently have a dedicated workflow branch; see [Supported Ticket
  Categories](#8-supported-ticket-categories).
- **Isolated per-agent state** — `SupportAgentState` extends the shared
  `AgentState` rather than modifying it, so the HR Agent and any future
  agent are unaffected by support-specific fields.
- **Graceful degradation** — a RAG retrieval failure (network, DB,
  embedding model) is caught and logged rather than crashing the graph; a
  malformed or low-confidence ticket-classification response degrades to
  `"Unknown"` rather than propagating bad data.
- **Node return style is mixed, by history rather than design** —
  `ticket_intake_node`, `ticket_classification_node`, and
  `retrieve_refund_policy_node` return partial-update dicts (the
  LangGraph-recommended pattern, matching `hr_agent`); the rest of the
  original nodes mutate and return the full state dict. Both are valid
  LangGraph node contracts, but unifying them is a worthwhile future
  cleanup (see [Future Improvements](#12-future-improvements)).

## 3. LangGraph Flow

`build_support_graph()` in `backend/app/agents/support_agent/graph.py`
compiles the following flow:

1. **`ticket_intake`** (entry point) — opens a ticket record unconditionally.
2. **`ticket_classification`** — classifies the ticket into a business
   category with a confidence score. Runs before routing, so it never
   affects which branch is taken.
3. **`classify_intent`** — a single LLM call decides `workflow`:
   `password_reset`, `order_status`, `refund_request`, or `unknown`. A
   conditional edge routes to the matching branch:
   - **`password_reset`** → `extract_account_details` → `send_password_reset` → END
   - **`order_status`** → `extract_order_details` → `retrieve_order_status` → `generate_order_status_response` → END
   - **`refund_request`** → `extract_refund_details` → `retrieve_refund_policy` (real RAG) → `evaluate_refund_request` → END
   - **`unknown`** → `unknown_intent` → END (fixed clarification message, no LLM call)

Every path — including the unknown fallback — ends with a populated
`ticket_id`, `ticket_category`, `workflow`, and `agent_response`.

## 4. Graph Diagram

```mermaid
flowchart TD
    A[ticket_intake] --> B[ticket_classification]
    B --> C[classify_intent]

    C -->|password_reset| D[extract_account_details]
    D --> E[send_password_reset]
    E --> Z([END])

    C -->|order_status| F[extract_order_details]
    F --> G[retrieve_order_status]
    G --> H[generate_order_status_response]
    H --> Z

    C -->|refund_request| I[extract_refund_details]
    I --> J["retrieve_refund_policy (shared RAG node)"]
    J --> K[evaluate_refund_request]
    K --> Z

    C -->|unknown| L[unknown_intent]
    L --> Z
```

`_route_by_workflow(state)` — the single conditional-edge selector — reads
`state["workflow"]` as set by `classify_intent_node`, defaulting to
`"unknown"` so an unrecognized future value can never dead-end the graph.

## 5. Nodes

| Node | Phase | Description |
|---|---|---|
| `ticket_intake_node` | Entry | Deterministic (no LLM): assigns `ticket_id`, `ticket_status="Open"`, a keyword-heuristic `ticket_priority`, and a placeholder `issue_category`. Only fills fields not already set. |
| `ticket_classification_node` | Entry | LLM call: classifies into one of 7 categories + confidence; gates low-confidence/unrecognized results to `"Unknown"`. See [Ticket Classification](#6-ticket-classification). |
| `classify_intent_node` | Entry | LLM call: single-word `workflow` classification (`password_reset` / `order_status` / `refund_request` / `unknown`). Drives the conditional edge. |
| `extract_account_details_node` | Password Reset | Placeholder extraction of `account_email` (defaults to `"Unknown"`). |
| `send_password_reset_node` | Password Reset | Marks `reset_link_sent=True` and drafts a confirmation message via LLM. No real auth system wired up. |
| `extract_order_details_node` | Order Status | Placeholder extraction of `order_id` (defaults to `"Unspecified"`). |
| `retrieve_order_status_node` | Order Status | Calls `rag.py`'s `lookup_order_status` — a fixed placeholder status, not a real order-management call. |
| `generate_order_status_response_node` | Order Status | Drafts a response summarizing order status via LLM. |
| `extract_refund_details_node` | Refund Request | Placeholder extraction of `order_id` and `refund_reason`. |
| `retrieve_refund_policy_node` | Refund Request | Delegates to the shared `rag_retrieval_node` for real pgvector-backed policy retrieval; try/except for graceful degradation. See [RAG Integration](#7-rag-integration). |
| `evaluate_refund_request_node` | Refund Request | Always sets `refund_decision="pending_manual_review"` (never auto-approves/denies) and drafts a response via LLM, using retrieved policy context. |
| `unknown_intent_node` | Fallback | Fixed clarification message, no LLM call. |

## 6. Ticket Classification

`ticket_classification_node` (in `nodes.py`) assigns each ticket a
business/reporting category, separate from workflow routing:

- **Prompt contract** (`TICKET_CLASSIFICATION_PROMPT` in `prompts.py`) asks
  the LLM to respond with strict JSON: `{"category": "...", "confidence":
  <0.0-1.0>}` — the same structured-JSON convention already used by
  `sales_agent.lead_qualification_node` and
  `marketing_agent.generate_content_node`, since `classify_intent_node`'s
  single-bare-word format can't carry a numeric confidence.
- **Category set**: `Refund`, `Password Reset`, `Billing`, `Technical
  Issue`, `Account Issue`, `Order Status`, `General Inquiry` (see
  [Supported Ticket Categories](#8-supported-ticket-categories)).
- **Confidence threshold**: `_TICKET_CATEGORY_CONFIDENCE_THRESHOLD = 0.6`
  (a new, locally-scoped constant — no project-wide threshold existed
  anywhere else in the repo). A response is downgraded to `"Unknown"` when
  either:
  - the category isn't one of the 7 recognized labels, or
  - `confidence < 0.6`.
- **Failure handling**: malformed JSON, a missing `category`/`confidence`
  key, or any LLM error is caught and defaults to `("Unknown", 0.0)` rather
  than raising.
- **Empty input short-circuit**: blank/whitespace-only `user_input` returns
  `("Unknown", 0.0)` without calling the LLM at all.

## 7. RAG Integration

Refund-policy retrieval is wired to the shared RAG pipeline — there is no
Support-Agent-specific retrieval implementation:

```
retrieve_refund_policy_node (nodes.py)
    -> rag_retrieval_node (backend/app/core/rag_node.py)
        -> retrieve_relevant_docs (backend/app/core/retrieval.py)
            -> embed_text (backend/app/core/embeddings.py, BAAI/bge-m3)
            -> pgvector cosine-distance query over the Document table
        -> merges retrieved context into state["system_prompt"]
```

- The retrieved context lands on the **inherited `system_prompt` field**
  (not a dedicated Support-Agent field) — `evaluate_refund_request_node`
  reads it via `state.get("system_prompt") or ""` when drafting the final
  response.
- **Graceful degradation**: `retrieve_refund_policy_node` wraps the call in
  try/except (mirroring `hr_agent.nodes.retrieve_leave_policy_node`'s
  pattern) — a retrieval/embedding/DB failure is logged and the graph
  continues with no policy context, rather than crashing.
- **Environment prerequisites**: this pipeline needs a real **Postgres
  database with the pgvector extension** (`DATABASE_URL` must not be
  SQLite — pgvector's `<=>` cosine-distance operator has no SQLite
  equivalent) and the `sentence-transformers` package (now pinned in
  `requirements.txt`).
- **Known gap**: no refund/support-specific documents have been ingested
  yet — only HR sample policy docs exist in the vector store today (via the
  root-level `ingest_docs.py`), and `retrieve_relevant_docs` has no
  per-agent source filter, so a populated store would currently return
  documents from any domain. See [Future
  Improvements](#12-future-improvements).

## 8. Supported Ticket Categories

| Category | Description | Dedicated Workflow Branch |
|---|---|---|
| Refund | Requesting a refund, return, or money back | Yes — `refund_request` |
| Password Reset | Resetting a password, locked out of an account | Yes — `password_reset` |
| Order Status | Tracking an order, delivery status | Yes — `order_status` |
| Billing | Payment methods, charges, invoices, subscription costs | No — routes to the `unknown` clarification fallback |
| Technical Issue | Something in the product/app/website not working | No — routes to the `unknown` clarification fallback |
| Account Issue | Account settings, profile, or access problems other than password reset | No — routes to the `unknown` clarification fallback |
| General Inquiry | Anything else that doesn't fit the categories above | No — routes to the `unknown` clarification fallback |
| Unknown | Assigned when the LLM's category isn't recognized, or its confidence falls below 0.6 | No — routes to the `unknown` clarification fallback |

`ticket_category` is always populated (never null) for reporting purposes,
even when `workflow` resolves to `unknown` — see the Billing/Technical
Issue/Account Issue/General Inquiry examples in [Example
Responses](#11-example-responses).

## 9. Testing Summary

```bash
python -m pytest test_support_agent_graph.py test_support_agent_nodes.py \
    test_support_agent_sample_tickets.py test_support_agent_comprehensive.py -v
```

| Test file | Focus | Count |
|---|---|---|
| `test_support_agent_graph.py` | End-to-end graph invocation for all 3 workflows + unknown fallback; ticket creation | 5 tests |
| `test_support_agent_nodes.py` | `ticket_intake_node` unit tests (priority heuristic, field preservation) | 13 tests |
| `test_support_agent_sample_tickets.py` | 25 realistic tickets across all 7 categories + unrelated/low-confidence requests, asserting category + workflow + response together | 4 tests, 25 subtests |
| `test_support_agent_comprehensive.py` | Graph compilation, RAG success/failure, ticket-classification unit tests (all categories, confidence boundary, malformed input), invalid/empty/unicode/very-long input, unknown-intent, end-to-end state shape, state isolation | 35 tests |

All tests are deterministic and require no network access or `GROQ_API_KEY`
— the LLM is stubbed via `unittest.mock.patch` on `get_llm`, and the shared
RAG node is stubbed via `patch.object` on `rag_retrieval_node`, consistent
with the HR Agent suite's conventions.

## 10. Example Requests

There is no HTTP endpoint yet, so the graph is invoked directly:

```python
from backend.app.agents.support_agent.graph import build_support_graph

graph = build_support_graph()

# Refund request
graph.invoke({
    "messages": [],
    "user_input": "I'd like a refund for order #4521, it arrived broken.",
    "agent_response": None,
    "agent_name": "support_agent",
})

# Password reset
graph.invoke({
    "messages": [],
    "user_input": "I forgot my password and I'm locked out of my account.",
    "agent_response": None,
    "agent_name": "support_agent",
})

# Billing (a recognized ticket category with no dedicated workflow branch)
graph.invoke({
    "messages": [],
    "user_input": "I was charged twice for my subscription this month.",
    "agent_response": None,
    "agent_name": "support_agent",
})
```

## 11. Example Responses

**Refund request** (final state, abridged):
```json
{
  "ticket_id": "TCK-4F2A9B10",
  "ticket_status": "Open",
  "ticket_category": "Refund",
  "ticket_category_confidence": 0.93,
  "workflow": "refund_request",
  "refund_decision": "pending_manual_review",
  "agent_response": "Your refund request has been submitted for manual review."
}
```

**Password reset** (final state, abridged):
```json
{
  "ticket_id": "TCK-9C13E7A2",
  "ticket_status": "Open",
  "ticket_category": "Password Reset",
  "ticket_category_confidence": 0.9,
  "workflow": "password_reset",
  "reset_link_sent": true,
  "agent_response": "A password reset link has been sent to your account email."
}
```

**Billing** (recognized category, no dedicated workflow — routes to the
clarification fallback; demonstrates that `ticket_category` and `workflow`
are independent):
```json
{
  "ticket_id": "TCK-1D77B043",
  "ticket_status": "Open",
  "ticket_category": "Billing",
  "ticket_category_confidence": 0.79,
  "workflow": "unknown",
  "agent_response": "I can currently help with password resets, order status, and refund requests. Could you clarify which of these you need help with?"
}
```

**Off-topic / low confidence** (final state, abridged):
```json
{
  "ticket_id": "TCK-77AA0921",
  "ticket_status": "Open",
  "ticket_category": "Unknown",
  "ticket_category_confidence": 0.35,
  "workflow": "unknown",
  "agent_response": "I can currently help with password resets, order status, and refund requests. Could you clarify which of these you need help with?"
}
```

## 12. Future Improvements

- **HTTP API layer** — add `backend/app/api/support.py` +
  `backend/app/schemas/support.py`, mirroring `api/hr.py`'s `POST
  /hr/message` pattern, so the graph is reachable over HTTP like the HR
  Agent.
- **Expand workflow coverage** — Billing, Technical Issue, Account Issue,
  and General Inquiry are recognized ticket categories but have no
  dedicated automated workflow yet; they all fall back to the clarification
  message.
- **Real order-management / auth / payments integration** — replace the
  placeholder `lookup_order_status`, `send_password_reset_node`, and
  `evaluate_refund_request_node`'s auto-review-only decision with real
  backend system calls.
- **Structured LLM extraction** — replace the `setdefault("...",
  "Unknown"/"Unspecified")` placeholders in the extraction nodes with real
  structured extraction (tool/function calling) or explicit form input.
- **Ingest real support/refund documents and scope retrieval by source** —
  only HR sample documents exist in the vector store today;
  `core/retrieval.py`'s `retrieve_relevant_docs` also has no per-agent
  source filter, so a populated multi-domain store would currently mix
  results across agents.
- **Unify node return style** — some nodes return partial-update dicts
  (`ticket_intake_node`, `ticket_classification_node`,
  `retrieve_refund_policy_node`), others mutate and return the full state;
  worth standardizing on the partial-dict convention throughout.
- **Conversation persistence** — invocation is currently stateless (one
  message in, one response out); LangGraph checkpointing would enable
  multi-turn conversations.
- **Rate limiting / request logging** — no throttling or structured request
  logging exists yet, same gap noted in `HR_AGENT.md`.
