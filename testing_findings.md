# HR Agent — Leave Request Flow: Scaffold Testing Findings

## Objective

Verify that the shared LangGraph scaffold (`backend/app/core`) correctly
powers the HR Agent's **Leave Request** workflow end-to-end: that the
compiled graph (`build_hr_graph()`) executes without error, routes a leave
request to the correct branch, runs each node in the expected order, and
that `HRAgentState` is updated with the correct fields at each step — without
making any changes to the existing HR Agent implementation.

## Test Flow

1. A standalone test script was written (kept outside the `hr_agent` package,
   in a scratch location — no HR Agent source files were modified).
2. The script monkeypatches `backend.app.agents.hr_agent.nodes.get_llm` at
   runtime with a `FakeLLM` stand-in, so the graph runs with no network call
   / Groq API key required. The fake:
   - returns `"leave_request"` for the intent-classification prompt
     (identified by the phrase `"intent classifier"`), and
   - returns a canned acknowledgement string for the leave-evaluation prompt
     (identified by the phrase `"processing a leave request"`).
   - This only replaces the LLM call; the real graph, routing, and node
     logic from `hr_agent/graph.py` and `hr_agent/nodes.py` run unmodified.
3. `build_hr_graph()` was called to compile the real HR Agent graph.
4. A toy conversational input was submitted as the initial `HRAgentState`:
   > "Hi, I'm not feeling well and need to take sick leave from Aug 1 to
   > Aug 3. Can you submit this for me?"
5. The graph was invoked via `graph.invoke(initial_state)` and the resulting
   state was inspected field-by-field.

## Expected Result

- `classify_intent_node` sets `state["workflow"] = "leave_request"`.
- The conditional edge routes to the leave-request branch:
  `extract_leave_details` → `retrieve_leave_policy` → `evaluate_leave_request`
  → `END`.
- `leave_type`, `leave_start_date`, `leave_end_date` are populated (with
  placeholder `"Unspecified"` values, since real NLU extraction is not yet
  implemented — this is documented as a known placeholder in `nodes.py`).
- `leave_policy_context` is populated with policy snippets returned by the
  RAG placeholder (`rag.py`) relevant to the user's message.
- `leave_decision` is set to `"pending_manual_review"` (the agent never
  auto-approves/denies, per the placeholder design).
- `agent_response` contains the drafted acknowledgement message.
- The onboarding branch is **not** executed — onboarding-only fields
  (`employee_name`, `employee_role`, `onboarding_checklist`) remain unset.

## Actual Result

Final state returned by `graph.invoke()`:

```json
{
  "messages": [],
  "user_input": "Hi, I'm not feeling well and need to take sick leave from Aug 1 to Aug 3. Can you submit this for me?",
  "agent_response": "Thanks for letting us know! Your sick leave request for Aug 1-3 has been submitted and is pending manual review by HR. We'll follow up within 2 business days.",
  "agent_name": "hr_agent",
  "workflow": "leave_request",
  "leave_type": "Unspecified",
  "leave_start_date": "Unspecified",
  "leave_end_date": "Unspecified",
  "leave_policy_context": [
    "Full-time employees accrue 1.5 days of paid time off per month.",
    "Sick leave requests do not require advance notice but do require manager notification as soon as possible.",
    "Leave requests longer than 5 consecutive days require manager approval at least 2 weeks in advance."
  ],
  "leave_decision": "pending_manual_review"
}
```

Onboarding-only fields, checked directly on the same result object:

| Field                  | Value  |
|-------------------------|--------|
| `employee_name`         | `None` |
| `employee_role`         | `None` |
| `onboarding_checklist`  | `None` |

The graph executed with no exceptions and terminated at `END` after exactly
the three leave-request nodes.

## Findings

- **Routing works correctly.** `classify_intent_node` classified the toy
  message as `"leave_request"`, and the conditional edge sent execution down
  the correct branch only. Onboarding fields stayed `None` — proof
  `extract_employee_details_node` (which would set them to `"Unknown"` via
  `setdefault`) never ran. This confirms the branches are mutually exclusive.
- **State accumulates correctly across nodes.** Each node in the branch
  (`extract_leave_details` → `retrieve_leave_policy` →
  `evaluate_leave_request`) added its own fields to the shared state dict
  without clobbering fields set by earlier nodes (e.g. `workflow` set by the
  classifier was still intact in the final state).
- **RAG placeholder retrieval is functioning as designed.** `rag.py`'s
  keyword-matching `retrieve_leave_policy()` correctly surfaced the
  sick-leave and general PTO policy snippets relevant to the input text,
  and correctly excluded the unrelated parental-leave snippet.
- **Placeholder logic behaves as documented, not as a bug.** `leave_type`,
  `leave_start_date`, and `leave_end_date` came back as `"Unspecified"`
  because `extract_leave_details_node` intentionally has no real NLU
  extraction yet (flagged in its docstring as a future integration point).
  This is expected scaffold behavior, not a defect.
- **The shared core scaffold integrates cleanly.** `HRAgentState` (a
  `TypedDict` subclass of the shared `AgentState`) worked as a drop-in
  `StateGraph` state type, and `evaluate_leave_request_node`'s call through
  the shared `get_llm()` indirection was successfully swapped for a fake at
  test time with zero changes to `hr_agent` source — confirming the shared
  `llm_client.get_llm()` abstraction is a clean seam for testing/mocking.
- **No HR Agent files were modified.** `git status` was checked before and
  after the test run; only this report file and the scratch test script
  (outside the repo) were added.

## Conclusion

The shared LangGraph scaffold, as consumed by the HR Agent's Leave Request
workflow, works correctly: the graph compiles, routes based on classified
intent, executes the correct sequence of nodes, and produces a consistent,
correctly-populated final state. The only gaps observed are the
intentionally-placeholder pieces already called out in the HR Agent's own
code comments (free-text field extraction and the RAG knowledge base), not
scaffold or graph-wiring defects. The HR Agent's leave-request flow is ready
to have its placeholder pieces replaced with real integrations without any
changes needed to the graph structure or shared core scaffold.
