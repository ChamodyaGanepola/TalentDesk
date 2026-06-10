import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

_embedding_cache = {}


def get_embedding(text: str):
    if not text or not text.strip():
        return []

    key = text.strip().lower()

    if key in _embedding_cache:
        return _embedding_cache[key]

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=key
    )

    embedding = response.data[0].embedding
    _embedding_cache[key] = embedding

    return embedding


def cosine_similarity(a, b):
    if not a or not b:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)