from sqlmodel import Session, SQLModel
from backend.app.db.database import engine
from backend.app.models.document import Document
from backend.app.core.embeddings import embed_text

# Sample HR-related documents to test our RAG pipeline with.
SQLModel.metadata.create_all(engine)
sample_docs = [
    "Employees are entitled to 20 paid leave days per year, which reset every January.",
    "To request leave, submit a request through the HR system with your start date, end date, and reason.",
    "Sick leave requires a doctor's note if taken for more than 3 consecutive days.",
    "New employees complete a 3-month probation period before becoming permanent staff.",
    "The standard work week is 40 hours, Monday to Friday, with flexible start times between 8-10 AM.",
]

with Session(engine) as session:
    for doc_text in sample_docs:
        embedding = embed_text(doc_text)  # convert the text into a vector
        doc = Document(content=doc_text, source="hr_policy_sample", embedding=embedding)
        session.add(doc)
    session.commit()
    print(f"Ingested {len(sample_docs)} sample documents!")