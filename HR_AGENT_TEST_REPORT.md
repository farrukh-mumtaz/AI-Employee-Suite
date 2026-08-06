# HR Agent — Test Report

## Scope

Target under test: `backend/app/agents/hr_agent/` (`graph.py`, `nodes.py`,
`state.py`, `extraction.py`, `prompts.py`, `rag.py`), built on the shared
scaffold in `backend/app/core/` (`graph.py`, `state.py`, `llm_client.py`).

## 1. Existing coverage (reviewed, not modified)

The HR Agent already had a substantial test suite at the repo root:

| File | Focus |
|---|---|
| `test_hr_agent.py` | End-to-end graph invocation for all three workflows (onboarding, leave request, unknown), via `unittest.mock.patch` on `get_llm` |
| `test_hr_agent_nodes.py` | Each node function in isolation — partial-update contract, LLM-failure fallbacks |
| `test_hr_agent_graph.py` | The two conditional-edge selector functions (`_route_by_workflow`, `_route_by_leave_decision`) in isolation |
| `test_hr_agent_extraction.py` | Pure regex/keyword heuristics in `extraction.py` |

This existing suite already covers: happy-path onboarding and leave-request
flows, the unknown-intent fallback, both leave decision branches, LLM
failure fallbacks, and the "don't overwrite pre-supplied fields" contract at
the node level. All 47 pre-existing tests were re-run and still pass
unmodified.

## 2. Gaps identified and filled

Reviewing the graph, nodes, state, extraction, prompts, and RAG modules
against the task's validation checklist surfaced gaps not covered by the
existing files. A new file, **`test_hr_agent_comprehensive.py`** (26 tests,
7 test classes), was added to fill them without duplicating existing tests:

| Test class | Fills the gap |
|---|---|
| `GraphCompilationTests` | No prior test asserted `build_hr_graph()` compiles cleanly, is safely repeatable, or exposes the documented node set (`graph.get_graph().nodes`) |
| `RetrieveLeavePolicyTests` | `rag.py` had zero direct unit test coverage anywhere in the suite (empty query, keyword match, no-overlap fallback, `top_k` limiting) |
| `GraphInvalidAndEmptyInputTests` | Empty/whitespace input was only tested against `classify_intent_node` in isolation, never through the full compiled graph; adds missing `user_input` key, `None` input, numeric-only, unicode/emoji, and a 500x-repeated long input |
| `OnboardingRealisticScenarioTests` | Additional realistic multi-field phrasings (full details extracted together with checklist + welcome message; partial details with no article before the job title; pre-supplied fields surviving a full graph run, not just the node) |
| `LeaveRequestRealisticScenarioTests` | Additional leave types (maternity, unpaid), single-day date collapsing, and the two *other* partial-information combinations (type known/dates missing, dates known/type unrecognized) that the existing suite didn't exercise at the graph level |
| `StateIsolationTests` | Whether a single compiled graph instance, reused across multiple `invoke()` calls (as it would be in a real process), leaks state or mutates the shared checklist template between calls |
| `FinalStateShapeTests` | Base `AgentState` fields (`user_input`, `agent_name`, `messages`) surviving intact across every branch |

All new tests reuse the same conventions as the existing suite: a
self-contained `FakeLLM`/`FakeResponse` stand-in patched onto
`backend.app.agents.hr_agent.nodes.get_llm` (mirroring `test_hr_agent.py`'s
approach exactly, so both files' expectations of the LLM stay consistent),
`unittest.TestCase`, and a local `_initial_state()` helper. No mocking
framework or fixture style was introduced that isn't already used
elsewhere in the repo.

## 3. Bugs found

**None.** No defect in `hr_agent` production code was found or fixed. Per
the task instructions, no production files were modified.

Two things worth flagging as *known, already-documented* behavior rather
than bugs (no fix applied):

- **`extract_role`** requires an article ("as **a**/**an** ...") or an
  explicit "role:"/"position:" marker. Phrasing like "starts as Junior
  DevOps Engineer" (no article) does not match, and role falls back to
  `"Unknown"`. This is a direct consequence of the intentionally simple,
  documented heuristic in `extraction.py` (not a full NLU pipeline) —
  covered by `test_partial_details_fall_back_to_unknown_placeholders`.
- **`rag.retrieve_leave_policy`**'s keyword match is a loose per-word
  substring test, so common short words can match broadly; when nothing
  overlaps at all it falls back to the general policy set rather than
  returning nothing. Confirmed as the documented "placeholder ... simple
  keyword matching" behavior, not a defect — covered by
  `test_no_keyword_overlap_falls_back_to_general_docs`.

Both are called out in the source as future integration points and were
left untouched.

## 4. Summary of tests created

- **File added:** `test_hr_agent_comprehensive.py`
- **26 new tests** across 7 classes (see table above), all passing.
- **73 total HR Agent tests** in the repo after this change (47 pre-existing + 26 new), all passing.

## 5. Files added or modified

| File | Change |
|---|---|
| `test_hr_agent_comprehensive.py` | Added (new) |
| `HR_AGENT_TEST_REPORT.md` | Added (this report) |
| Production code (`backend/app/agents/hr_agent/*`, `backend/app/core/*`) | **Not modified** |

## 6. How to run

```bash
# New file only
python -m pytest test_hr_agent_comprehensive.py -v

# Full HR Agent suite
python -m pytest test_hr_agent.py test_hr_agent_extraction.py test_hr_agent_graph.py test_hr_agent_nodes.py test_hr_agent_comprehensive.py -v
```

(`python -m unittest <file> -v` also works for any individual file, matching the existing suite's documented run command.)

## 7. Expected output

```
==================== 73 passed, 3 subtests passed in ~1.3s ====================
```

No network access or `GROQ_API_KEY` is required — every test that would
otherwise call the LLM patches `get_llm` with a deterministic fake.
