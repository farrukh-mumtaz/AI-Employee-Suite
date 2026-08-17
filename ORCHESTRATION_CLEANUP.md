# Orchestration Cleanup — Findings & Decision

## Issue
Two separate orchestration implementations existed in the codebase:
- `orchestration.py` (POST /orchestrate/) — used a generic placeholder graph for all agents, not connected to the real HR/Support agents
- `orchestrator.py` (POST /agent/message) — properly routes to the actual HR Agent and Support Agent graphs, but was missing authentication and interaction logging

## Decision
Kept `orchestrator.py` as the single orchestration layer, since it's the one actually wired up to the real agent graphs. Removed `orchestration.py`, which was only using a placeholder scaffold.

## Changes Made
- Added authentication (`get_current_user`) to `orchestrator.py` so only logged-in users can route messages
- Added interaction logging (`AgentLog`) so orchestrator activity now shows up in dashboard metrics, matching the rest of the backend
- Removed `orchestration.py` and its router registration in `main.py`

## Also Found & Fixed
- `requirements.txt` was missing several packages (`pgvector`, `passlib`, `python-jose`, `python-multipart`, `langgraph`, `langchain-anthropic`, `langchain-core`, `langchain-groq`) — a fresh clone could not run without manually installing these. Regenerated the file to include everything currently in use.