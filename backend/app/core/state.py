from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    messages: List[dict]
    user_input: str
    agent_response: Optional[str]
    agent_name: str