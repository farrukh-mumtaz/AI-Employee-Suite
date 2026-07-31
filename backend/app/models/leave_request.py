from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# This table stores leave requests submitted by employees.
# "status" tracks whether HR has approved, rejected, or not yet reviewed it.
class LeaveRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id")  # links this request to an employee
    start_date: datetime  # first day of leave
    end_date: datetime  # last day of leave
    reason: str  # why the employee is requesting leave
    status: str = Field(default="pending")  # "pending", "approved", or "rejected"
    created_at: datetime = Field(default_factory=datetime.utcnow)