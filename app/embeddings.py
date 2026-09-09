from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings


@lru_cache
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed_passage(text: str) -> list[float]:
    """Embedding de un fragmento de la base (para indexar)."""
    # Los modelos E5 requieren el prefijo "passage:"/"query:" — sin él, la
    # similitud coseno entre pregunta y fragmento se degrada notablemente.
    # Ver https://huggingface.co/intfloat/multilingual-e5-small
    return get_embedder().encode(f"passage: {text}", normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    """Embedding de una pregunta del usuario (para buscar)."""
    return get_embedder().encode(f"query: {text}", normalize_embeddings=True).tolist()
