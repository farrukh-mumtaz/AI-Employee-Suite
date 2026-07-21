from fastapi import FastAPI
from sqlalchemy import text
from database import engine

app = FastAPI(title="AI Employee Suite Backend")

@app.on_event("startup")
def on_startup():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

@app.get("/")
def read_root():
    return {"message": "AI Employee Suite backend is up and running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
