# Placeholder retrieval-augmented-generation layer for the Support Agent.
#
# Future integration point: swap `_PLACEHOLDER_REFUND_POLICY_DOCS` and
# `retrieve_refund_policy` for a real vector store (e.g. pgvector, Chroma,
# Pinecone) populated with the company's actual support/refund policy
# documents, and embed queries with the shared llm_client's embedding model
# once one is added to backend/app/core. Mirrors hr_agent/rag.py.
from typing import List, Optional

# Stand-in "knowledge base" until a real document store is wired up.
_PLACEHOLDER_REFUND_POLICY_DOCS = [
    "Refunds are eligible within 30 days of purchase with proof of purchase.",
    "Digital goods are non-refundable once downloaded or activated.",
    "Damaged or defective items are eligible for a full refund or replacement.",
    "Refunds are processed to the original payment method within 5-7 business days.",
]


def retrieve_refund_policy(query: str, top_k: int = 3) -> List[str]:
    """Return the top-k most relevant refund policy snippets for `query`.

    Placeholder implementation: does simple keyword matching over an
    in-memory list rather than real semantic search. Replace with an actual
    retriever (vector similarity search) once a policy document store
    exists.
    """
    if not query:
        return _PLACEHOLDER_REFUND_POLICY_DOCS[:top_k]

    query_lower = query.lower()
    scored = [
        doc for doc in _PLACEHOLDER_REFUND_POLICY_DOCS if any(
            word in doc.lower() for word in query_lower.split()
        )
    ]

    # Fall back to returning the general policy set if nothing matched, so
    # downstream nodes always have some context to work with.
    return (scored or _PLACEHOLDER_REFUND_POLICY_DOCS)[:top_k]


def lookup_order_status(order_id: Optional[str]) -> str:
    """Look up the status of an order.

    Placeholder implementation: no order-management system is wired up yet,
    so this always returns a fixed placeholder status. Future integration
    point: replace with a real call to the order/shipping backend (e.g. an
    internal orders API or database query) keyed on `order_id`.
    """
    if not order_id or order_id == "Unspecified":
        return "Unknown -- no order ID provided"
    return "Processing -- status lookup not yet integrated"
