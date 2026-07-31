from fastapi import FastAPI
from sqlalchemy import text
from sqlmodel import SQLModel
from backend.app.db.database import engine
from backend.app import models  # ensures all models are registered
from backend.app.api.auth import router as auth_router
from backend.app.api.hr import router as hr_router

app = FastAPI(title="AI Employee Suite Backend")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

app.include_router(auth_router)
app.include_router(hr_router)

@app.get("/")
def read_root():
    return {"message": "AI Employee Suite backend is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}