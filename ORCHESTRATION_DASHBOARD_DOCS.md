# Orchestration Layer & Dashboard APIs

## Orchestration Layer

### POST /orchestrate/
Central endpoint that routes a request to the correct agent based on `agent_name`, runs that agent's LangGraph, and logs the interaction for dashboard metrics.

Body: `{ "agent_name": str, "user_input": str, "system_prompt": str (optional) }`

Supported agent_name values: "hr", "sales", "support", "marketing" (currently all use the shared base scaffold; specific agent graphs can be registered in `AGENT_REGISTRY` in `orchestration.py`).

## Dashboard APIs

All dashboard endpoints require admin role.

### GET /dashboard/metrics
Returns high-level counts: total employees, total/pending leave requests, total agent interactions.

### GET /dashboard/agent-activity
Returns usage count per agent (how many times each agent was used).

### GET /dashboard/recent-activity
Returns the 10 most recent agent interactions.

## Notes

- Agent activity is tracked via the `AgentLog` table, populated automatically by the orchestration endpoint.
- As Samia and Abdul's specific agent graphs (HR, Sales, Support, Marketing) are finalized, they should be registered in `AGENT_REGISTRY` in place of the shared base scaffold.

## Performance & Monitoring (Completed)

### DB Query Optimization
Added indexes on `agentlog.agent_name`, `agentlog.created_at`, and `leaverequest.status` to speed up dashboard queries as data grows.

### Error Logging & Monitoring
- Added an `ErrorLog` table and a global exception handler that catches any unhandled backend error, logs it to the database, and returns a safe error response.
- `GET /dashboard/errors` (admin only) returns the 20 most recent errors for monitoring backend and agent health.

### Live Dashboard Connection
All dashboard endpoints query the database directly on every request (no caching), so metrics and activity always reflect the latest data as soon as an agent interaction happens through `/orchestrate/`.