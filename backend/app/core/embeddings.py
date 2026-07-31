from sentence_transformers import SentenceTransformer

# We load the model only once and reuse it, since loading is slow.
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # BAAI/bge-m3 is a strong multilingual embedding model, recommended for this task.
        _model = SentenceTransformer("BAAI/bge-m3")
    return _model

# Converts a piece of text into a list of numbers (embedding) representing its meaning.
def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()