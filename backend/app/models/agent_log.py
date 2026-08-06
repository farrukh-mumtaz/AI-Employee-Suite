from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# This table logs every time an agent is used, so we can build dashboard metrics
# (e.g. "how many times was the HR agent used today").
class AgentLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_name: str  # e.g. "hr", "sales", "support", "marketing"
    user_input: str  # what the user asked
    agent_response: str  # what the agent replied
    created_at: datetime = Field(default_factory=datetime.utcnow)