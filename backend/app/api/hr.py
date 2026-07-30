from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.app.db.database import get_session
from backend.app.models.employee import Employee
from backend.app.models.leave_request import LeaveRequest
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.models.user import User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/hr", tags=["hr"])

# --- Request body shapes ---

class EmployeeCreate(BaseModel):
    name: str
    department: str
    position: str

class LeaveRequestCreate(BaseModel):
    employee_id: int
    start_date: datetime
    end_date: datetime
    reason: str

class LeaveStatusUpdate(BaseModel):
    status: str  # "approved" or "rejected"

# --- Employee endpoints ---

# Creates a new employee record. Only logged-in users can do this.
@router.post("/employees")
def create_employee(data: EmployeeCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = Employee(name=data.name, department=data.department, position=data.position)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee

# Returns a list of all employees.
@router.get("/employees")
def list_employees(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employees = session.exec(select(Employee)).all()
    return employees

# Returns a single employee by their ID.
@router.get("/employees/{employee_id}")
def get_employee(employee_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

# --- Leave request endpoints ---

# Submits a new leave request for an employee. Starts as "pending".
@router.post("/leaves")
def create_leave_request(data: LeaveRequestCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = session.get(Employee, data.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    leave = LeaveRequest(
        employee_id=data.employee_id,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason
    )
    session.add(leave)
    session.commit()
    session.refresh(leave)
    return leave

# Returns all leave requests (for HR/admin to review).
@router.get("/leaves")
def list_leave_requests(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    leaves = session.exec(select(LeaveRequest)).all()
    return leaves

# Updates a leave request's status (approve/reject). Only admins can do this.
@router.patch("/leaves/{leave_id}")
def update_leave_status(leave_id: int, data: LeaveStatusUpdate, session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    leave = session.get(LeaveRequest, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave.status = data.status
    session.add(leave)
    session.commit()
    session.refresh(leave)
    return leave