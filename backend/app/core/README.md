# Shared Agent Scaffold

This is the shared base that every AI agent (HR, Sales, Marketing, Support) is built on top of. Instead of each agent writing its own code to talk to the AI, manage conversation state, or handle errors, everyone uses this same foundation — so we stay consistent and don't repeat work.

## What's in here

- **`state.py`** — defines the shape of data (`AgentState`) that flows through an agent while it runs
- **`llm_client.py`** — a single function that connects to the AI model (currently using Groq for testing)
- **`graph.py`** — the base LangGraph graph: takes user input, sends it to the AI, returns a response

## How to use this for your own agent

You don't need to touch these files. Just import what you need and build on top.

### 1. Import the base pieces

```python
from backend.app.core.state import AgentState
from backend.app.core.llm_client import get_llm
from langgraph.graph import StateGraph, END
```

### 2. Give your agent a system prompt

This is how you make the AI behave like your specific agent (HR, Sales, etc.) instead of a generic assistant. Pass it in when you call the graph:

```python
result = graph.invoke({
    "messages": [],
    "user_input": "What's our leave policy?",
    "agent_response": None,
    "agent_name": "hr",
    "system_prompt": "You are an HR assistant for a tech company. Answer employee questions about policies clearly and briefly."
})
```

Just change the `system_prompt` text to match your agent's role, and the same underlying graph will behave differently.

### 3. If your agent needs more than one step

The base graph (`build_base_graph()`) only has one step: call the AI, done. If your agent needs multiple steps — like Abdul's Sales Agent, which needs to classify intent, then branch into different actions — you'll build your own graph using the same pattern, just with more nodes and edges.

Example shape for a multi-step agent:

```python
def classify_intent_node(state: AgentState) -> AgentState:
    # your logic here
    return state

def notify_sales_node(state: AgentState) -> AgentState:
    # your logic here
    return state

graph = StateGraph(AgentState)
graph.add_node("classify_intent", classify_intent_node)
graph.add_node("notify_sales", notify_sales_node)
graph.set_entry_point("classify_intent")
graph.add_conditional_edges(
    "classify_intent",
    lambda state: "notify_sales" if state["agent_response"] == "qualified_lead" else END
)
graph.add_edge("notify_sales", END)
compiled_graph = graph.compile()
```

Each node is just a function that takes the state, does something, and returns the updated state — same pattern as the base scaffold, just chained together.

## Notes

- Error handling is already built in — if the AI call fails, `agent_response` will contain a friendly error message instead of crashing the app.
- Currently using **Groq** for testing (free tier). This may switch to Claude/Anthropic later — since everyone goes through `get_llm()`, that change will only need to happen in one place.
- Questions? Ping Yumna.