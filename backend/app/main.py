from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import SQLModel, Session
from backend.app.db.database import engine
from backend.app import models
from backend.app.api.auth import router as auth_router
from backend.app.api.hr import router as hr_router
from backend.app.api.orchestration import router as orchestration_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.models.error_log import ErrorLog
from backend.app.api.orchestrator import router as orchestrator_router
from backend.app.api.support import router as support_router

app = FastAPI(title="AI Employee Suite Backend")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

app.include_router(auth_router)
app.include_router(hr_router)
app.include_router(orchestration_router)
app.include_router(dashboard_router)

# This catches any unhandled error anywhere in the backend, logs it to the database
# for monitoring, and still returns a proper error response to the user.
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    with Session(engine) as session:
        log_entry = ErrorLog(source=str(request.url.path), error_message=str(exc))
        session.add(log_entry)
        session.commit()
    return JSONResponse(status_code=500, content={"detail": "Internal server error, this has been logged."})
app.include_router(support_router)
app.include_router(orchestrator_router)

@app.get("/")
def read_root():
    return {"message": "AI Employee Suite backend is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}