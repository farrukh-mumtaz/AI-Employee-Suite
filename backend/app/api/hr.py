# HR Agent API router.
#
# Combines two concerns under a single "/hr" prefix:
#   1. The conversational HR Agent LangGraph endpoint (POST /hr/message),
#      bridging the FastAPI layer to the existing HR Agent graph
#      (backend/app/agents/hr_agent/graph.py) without modifying it. The
#      compiled graph is built once at import time -- LangGraph's compiled
#      graphs are stateless/reusable across invocations, so there's no need
#      to rebuild it per request.
#   2. The database-backed HR record-keeping endpoints (Employee / Leave
#      Request CRUD) from main, authenticated via the shared JWT
#      dependencies in backend/app/core/dependencies.py.
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.app.agents.hr_agent.graph import build_hr_graph
from backend.app.core.dependencies import get_current_user, require_role
from backend.app.db.database import get_session
from backend.app.models.employee import Employee
from backend.app.models.leave_request import LeaveRequest
from backend.app.models.user import User
from backend.app.schemas.hr import HRAgentRequest, HRAgentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["hr"])

# --- HR Agent (LangGraph conversational) endpoint ---

_hr_graph = build_hr_graph()


@router.post("/message", response_model=HRAgentResponse)
def send_hr_message(request: HRAgentRequest) -> HRAgentResponse:
    """Run a single message through the HR Agent graph and return its response.

    Each call is a fresh, independent graph run (no conversation state is
    persisted between requests) -- matching how the graph is exercised in
    the existing test suite (test_hr_agent.py et al.).
    """
    initial_state = {
        "messages": [],
        "user_input": request.user_input,
        "agent_response": None,
        "agent_name": "hr_agent",
    }

    try:
        final_state = _hr_graph.invoke(initial_state)
    except Exception:
        logger.exception("HR agent graph invocation failed")
        raise HTTPException(status_code=500, detail="HR agent failed to process the request")

    agent_response = final_state.get("agent_response")
    if not agent_response:
        logger.error("HR agent graph returned no agent_response for state: %s", final_state)
        raise HTTPException(status_code=500, detail="HR agent produced no response")

    return HRAgentResponse(
        agent_response=agent_response,
        workflow=final_state.get("workflow", "unknown"),
        employee_name=final_state.get("employee_name"),
        employee_role=final_state.get("employee_role"),
        start_date=final_state.get("start_date"),
        onboarding_checklist=final_state.get("onboarding_checklist"),
        leave_type=final_state.get("leave_type"),
        leave_start_date=final_state.get("leave_start_date"),
        leave_end_date=final_state.get("leave_end_date"),
        leave_reason=final_state.get("leave_reason"),
        leave_decision=final_state.get("leave_decision"),
    )


# --- Employee / Leave Request record-keeping endpoints (from main) ---

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
    status: str  # "approved", "rejected", or "pending"

# --- Employee endpoints ---

# Creates a new employee record. Only logged-in users can do this.
@router.post("/employees")
def create_employee(data: EmployeeCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    # Bug fix: empty employee names were being accepted, now rejected
    if not data.name or len(data.name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Employee name cannot be empty")

    employee = Employee(name=data.name, department=data.department, position=data.position)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee

# Returns a paginated list of employees, for cleaner dashboard/table display.
@router.get("/employees")
def list_employees(skip: int = 0, limit: int = 20, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employees = session.exec(select(Employee).offset(skip).limit(limit)).all()
    return employees

# Returns a single employee by their ID.
@router.get("/employees/{employee_id}")
def get_employee(employee_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

# Updates an existing employee's details (name, department, position).
@router.patch("/employees/{employee_id}")
def update_employee(employee_id: int, data: EmployeeCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.name = data.name
    employee.department = data.department
    employee.position = data.position
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee

# --- Leave request endpoints ---

# Submits a new leave request for an employee. Starts as "pending".
# Validates that the employee exists and that the date range makes sense.
@router.post("/leaves")
def create_leave_request(data: LeaveRequestCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    employee = session.get(Employee, data.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Bug fix: previously allowed end_date before start_date, which made no sense
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date")

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
# Bug fix: previously accepted any string as status; now validates it's one of the allowed values.
@router.patch("/leaves/{leave_id}")
def update_leave_status(leave_id: int, data: LeaveStatusUpdate, session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    if data.status not in ["approved", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="status must be 'approved', 'rejected', or 'pending'")

    leave = session.get(LeaveRequest, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave.status = data.status
    session.add(leave)
    session.commit()
    session.refresh(leave)
    return leave