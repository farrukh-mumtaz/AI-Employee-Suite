from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# This table stores backend and agent errors, so we can monitor issues over time
# instead of only seeing them in the terminal (which disappears on restart).
class ErrorLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str  # where the error came from, e.g. "orchestration", "hr_agent", "backend"
    error_message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)