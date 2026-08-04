# Support Agent retrieval helpers.
#
# Refund-policy retrieval is handled by the shared RAG node
# (backend/app/core/rag_node.py -> backend/app/core/retrieval.py), which
# queries the real pgvector document store -- see retrieve_refund_policy_node
# in nodes.py for the wiring. This module now only holds order-status lookup,
# which is a transactional lookup rather than a document-retrieval concern.
from typing import Optional


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
