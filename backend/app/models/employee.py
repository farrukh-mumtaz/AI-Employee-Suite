from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# This table stores basic employee records for the HR system.
class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # employee's full name
    department: str  # e.g. "Engineering", "Sales"
    position: str  # e.g. "Software Engineer"
    leave_balance: int = Field(default=20)  # number of leave days remaining, default 20 per year
    created_at: datetime = Field(default_factory=datetime.utcnow)