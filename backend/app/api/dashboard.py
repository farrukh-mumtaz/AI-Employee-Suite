from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from backend.app.db.database import get_session
from backend.app.core.dependencies import require_role
from backend.app.models.user import User
from backend.app.models.agent_log import AgentLog
from backend.app.models.employee import Employee
from backend.app.models.leave_request import LeaveRequest
from backend.app.models.error_log import ErrorLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Dashboard access is restricted to admins only.

# Returns high-level counts for the CEO dashboard overview.
@router.get("/metrics")
def get_metrics(session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    total_employees = session.exec(select(func.count()).select_from(Employee)).one()
    total_leaves = session.exec(select(func.count()).select_from(LeaveRequest)).one()
    pending_leaves = session.exec(select(func.count()).select_from(LeaveRequest).where(LeaveRequest.status == "pending")).one()
    total_agent_calls = session.exec(select(func.count()).select_from(AgentLog)).one()

    return {
        "total_employees": total_employees,
        "total_leave_requests": total_leaves,
        "pending_leave_requests": pending_leaves,
        "total_agent_interactions": total_agent_calls,
    }

# Returns how many times each agent has been used, for the dashboard's activity breakdown.
@router.get("/agent-activity")
def get_agent_activity(session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    results = session.exec(
        select(AgentLog.agent_name, func.count().label("count"))
        .group_by(AgentLog.agent_name)
    ).all()
    return [{"agent_name": row[0], "count": row[1]} for row in results]

# Returns the most recent agent interactions, for a live activity feed on the dashboard.
@router.get("/recent-activity")
def get_recent_activity(session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    logs = session.exec(
        select(AgentLog).order_by(AgentLog.created_at.desc()).limit(10)
    ).all()
    return logs


# Returns the most recent errors, for monitoring backend and agent health.
@router.get("/errors")
def get_recent_errors(session: Session = Depends(get_session), current_user: User = Depends(require_role(["admin"]))):
    errors = session.exec(
        select(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(20)
    ).all()
    return errors