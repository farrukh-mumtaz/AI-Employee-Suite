import time
from backend.app.core.retrieval import retrieve_relevant_docs
from backend.app.core.rag_node import make_rag_node

# Test 1: Basic retrieval still works
print("=== Test 1: Retrieval accuracy ===")
results = retrieve_relevant_docs("How many leave days do I get?", top_k=2)
for doc in results:
    print(f"- {doc}")

# Test 2: Caching - the same query should be much faster the second time
print("\n=== Test 2: Caching performance ===")
start = time.time()
retrieve_relevant_docs("What are the working hours?", top_k=2)
first_call_time = time.time() - start

start = time.time()
retrieve_relevant_docs("What are the working hours?", top_k=2)
second_call_time = time.time() - start

print(f"First call (not cached): {first_call_time:.4f} seconds")
print(f"Second call (cached): {second_call_time:.4f} seconds")

# Test 3: Configurable node (finalized interface)
print("\n=== Test 3: Configurable RAG node ===")
custom_node = make_rag_node(top_k=1)
state = {
    "messages": [],
    "user_input": "What happens if I'm sick?",
    "agent_response": None,
    "agent_name": "test",
    "system_prompt": "You are an HR assistant."
}
result_state = custom_node(state)
print("Updated system_prompt includes retrieved context:")
print(result_state["system_prompt"])