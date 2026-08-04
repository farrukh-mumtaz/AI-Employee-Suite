from sqlmodel import Session, select
from backend.app.db.database import engine
from backend.app.models.document import Document
from backend.app.core.embeddings import embed_text
from functools import lru_cache

# This cache stores results for repeated queries, so identical questions don't
# re-run the embedding model or hit the database again. maxsize=100 keeps the
# 100 most recent unique queries cached.
@lru_cache(maxsize=100)
def _cached_retrieve(query: str, top_k: int) -> tuple:
    query_embedding = embed_text(query)

    with Session(engine) as session:
        results = session.exec(
            select(Document)
            .order_by(Document.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        ).all()

    # Returning a tuple (not a list) because lru_cache requires hashable/consistent return types
    return tuple(doc.content for doc in results)

# Given a user's question, finds the most relevant documents from the vector database.
# Uses caching so repeated identical queries are instant.
def retrieve_relevant_docs(query: str, top_k: int = 3) -> list[str]:
    return list(_cached_retrieve(query, top_k))