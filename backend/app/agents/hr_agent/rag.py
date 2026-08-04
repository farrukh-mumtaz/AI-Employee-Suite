# Placeholder retrieval-augmented-generation layer for the HR Agent.
#
# Future integration point: swap `_PLACEHOLDER_POLICY_DOCS` and
# `retrieve_leave_policy` for a real vector store (e.g. pgvector, Chroma,
# Pinecone) populated with the company's actual HR policy documents, and
# embed queries with the shared llm_client's embedding model once one is
# added to backend/app/core.
from typing import List

# Stand-in "knowledge base" until a real document store is wired up.
_PLACEHOLDER_POLICY_DOCS = [
    "Full-time employees accrue 1.5 days of paid time off per month.",
    "Sick leave requests do not require advance notice but do require "
    "manager notification as soon as possible.",
    "Leave requests longer than 5 consecutive days require manager approval "
    "at least 2 weeks in advance.",
    "Parental leave policy: refer to the employee handbook, section 4.2.",
]


def retrieve_leave_policy(query: str, top_k: int = 3) -> List[str]:
    """Return the top-k most relevant HR policy snippets for `query`.

    Placeholder implementation: does simple keyword matching over an
    in-memory list rather than real semantic search. Replace with an actual
    retriever (vector similarity search) once a policy document store
    exists.
    """
    if not query:
        return _PLACEHOLDER_POLICY_DOCS[:top_k]

    query_lower = query.lower()
    scored = [
        doc for doc in _PLACEHOLDER_POLICY_DOCS if any(
            word in doc.lower() for word in query_lower.split()
        )
    ]

    # Fall back to returning the general policy set if nothing matched, so
    # downstream nodes always have some context to work with.
    return (scored or _PLACEHOLDER_POLICY_DOCS)[:top_k]
