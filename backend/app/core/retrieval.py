from sqlmodel import Session, select
from backend.app.db.database import engine
from backend.app.models.document import Document
from backend.app.core.embeddings import embed_text


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity -- used only by the non-Postgres
    fallback below, so it has no extra dependency (numpy) of its own."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Given a user's question, finds the most relevant documents from the vector database.
def retrieve_relevant_docs(query: str, top_k: int = 3) -> list[str]:
    query_embedding = embed_text(query)

    with Session(engine) as session:
        if engine.dialect.name == "postgresql":
            # Real pgvector similarity search via the `<=>` cosine-distance
            # operator -- the production path, unchanged.
            results = session.exec(
                select(Document)
                .order_by(Document.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            ).all()
            return [doc.content for doc in results]

        # Non-Postgres dialects (SQLite, used for local dev/tests) have no
        # equivalent to pgvector's `<=>` operator -- it's Postgres-specific
        # SQL syntax that SQLite's parser rejects outright. Fall back to
        # computing cosine similarity in Python over every row instead. This
        # is only meant for small local datasets; production always runs on
        # Postgres and takes the branch above.
        documents = session.exec(select(Document)).all()
        scored = sorted(
            documents,
            key=lambda doc: _cosine_similarity(doc.embedding, query_embedding),
            reverse=True,
        )
        return [doc.content for doc in scored[:top_k]]