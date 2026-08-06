# Manual RAG smoke-check script -- not a pytest test (no test_* functions,
# just prints). Guarded behind __main__ so pytest collecting this file
# doesn't trigger a real embedding-model load + DB query as a side effect
# of import; run it directly instead: `python test_rag.py`.
from backend.app.core.retrieval import retrieve_relevant_docs

if __name__ == "__main__":
    test_queries = [
        "How many leave days do I get?",
        "What happens if I'm sick for a week?",
        "What are the working hours?",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = retrieve_relevant_docs(query, top_k=2)
        for i, doc in enumerate(results, 1):
            print(f"  {i}. {doc}")