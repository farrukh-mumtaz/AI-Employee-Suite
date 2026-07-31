# RAG Pipeline Design

## Overview
This RAG (Retrieval-Augmented Generation) pipeline lets AI agents answer questions using real company documents instead of relying only on the LLM's general knowledge.

## Components

1. **Embedding Model**: BAAI/bge-m3 (via sentence-transformers) - converts text into 1024-dimensional vectors representing meaning.
2. **Vector Storage**: PostgreSQL with the pgvector extension - stores document embeddings alongside regular data, using cosine distance for similarity search.
3. **Document Model** (`models/document.py`): stores content, source, and embedding for each document chunk.
4. **Ingestion** (`ingest_docs.py`): converts raw text documents into embeddings and saves them to the database.
5. **Retrieval** (`core/retrieval.py`): given a user query, finds the top-k most similar documents using cosine distance.
6. **LangGraph Node** (`core/rag_node.py`): wraps retrieval as a reusable node that injects relevant context into the system prompt before the LLM call.

## How to Use in an Agent's Graph

Any agent (HR, Sales, etc.) can add `rag_retrieval_node` to their LangGraph flow before the LLM call node, so responses are grounded in real documents.

## Testing

Tested retrieval accuracy with sample HR policy questions (`test_rag.py`) - retrieved documents were relevant to each query's topic.

## Notes

- Currently using BGE-M3 as recommended. Other embedding models can be swapped in `core/embeddings.py` if needed.
- Sample documents are HR-focused for testing; real documents can be ingested the same way via `ingest_docs.py`.