from sqlalchemy import text
from backend.app.db.database import engine

# This creates an index on the embedding column, which makes similarity search much faster
# as the number of documents grows. Without this, every query scans all rows one by one.
with engine.connect() as conn:
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS document_embedding_idx "
        "ON document USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    ))
    conn.commit()
    print("Vector index created for faster RAG queries!")