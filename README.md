# AI Employee Suite - MVP v1.0

## Project Vision

The objective of this project is to design and develop the MVP of the SMJ AI Employee Suite. This is an AI-powered platform designed to help organizations automate HR, Sales, Marketing, Customer Support, and Executive decision-making through intelligent AI agents.

## Core Deliverables

By the end of the 8-week development cycle, this repository will contain:

* **AI HR Agent**

* **AI Sales Agent**

* **AI Marketing Agent**

* **AI Support Agent**

* **CEO Dashboard**


## GitHub Rules & Workflow

To maintain code quality, all team members must adhere to the following strict guidelines:

* Every feature must be developed in its own isolated branch.


* **No direct commits to the `main` branch are allowed.**

* Pull Requests (PRs) are mandatory for all code merges.


* All code must be reviewed by the Team Lead before merging.


* Daily commits are expected from every developer.



## Definition of Done (DoD)

A task is only considered complete and ready to merge when:

* The code is finished, tested successfully, and pushed to GitHub.


* The feature is fully documented (including API, Prompts, Flow Diagrams, and Test Cases).


* It is reviewed by the Team Lead and approved by the Founder.


* A demo has been completed.

## Testing

This scaffold has been tested end-to-end across three scenarios:

1. **Standard use case** — HR agent responding to a policy question, using a custom `system_prompt`. Confirmed the response matched the given role.
2. **Reusability across agents** — Same scaffold, different `system_prompt` (Sales agent). Confirmed the same code produces a completely different tone and behavior just by changing the prompt, proving the scaffold works generically across agent types.
3. **Missing system_prompt (edge case)** — Called the graph without providing a `system_prompt`. Confirmed it falls back gracefully to a default assistant behavior instead of crashing.

All three tests passed. Test files (`test_agent.py`, `test_sales.py`, `test_error.py`) are in the project root and can be run directly with `python <filename>.py` for reference.