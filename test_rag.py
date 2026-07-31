from backend.app.core.retrieval import retrieve_relevant_docs

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