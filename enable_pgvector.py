from sqlalchemy import text
from backend.app.db.database import engine

# This enables the pgvector extension in Postgres, which lets us store and search embeddings.
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()
    print("pgvector extension enabled!")