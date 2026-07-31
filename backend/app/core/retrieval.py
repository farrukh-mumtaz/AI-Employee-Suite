from sqlmodel import Session, select
from backend.app.db.database import engine
from backend.app.models.document import Document
from backend.app.core.embeddings import embed_text

# Given a user's question, finds the most relevant documents from the vector database.
def retrieve_relevant_docs(query: str, top_k: int = 3) -> list[str]:
    query_embedding = embed_text(query)

    with Session(engine) as session:
        results = session.exec(
            select(Document)
            .order_by(Document.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        ).all()

    return [doc.content for doc in results]