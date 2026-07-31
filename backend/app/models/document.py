from sqlmodel import SQLModel, Field, Column
from pgvector.sqlalchemy import Vector
from typing import Optional
from datetime import datetime

# This table stores document chunks along with their embeddings (numeric representation of meaning).
# BGE-M3 produces 1024-dimensional embeddings, so the vector column is sized accordingly.
class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str  # the actual text of the document chunk
    source: str = Field(default="sample")  # where this doc came from (e.g. "hr_policy.txt")
    embedding: list[float] = Field(sa_column=Column(Vector(1024)))  # the embedding vector
    created_at: datetime = Field(default_factory=datetime.utcnow)