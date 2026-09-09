from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embed_query
from app.models import Chunk, Document


@dataclass
class RetrievedChunk:
    label: str
    content: str
    document_title: str
    url: str
    similarity: float


def retrieve(db: Session, question: str, top_k: int) -> list[RetrievedChunk]:
    """Busca los `top_k` fragmentos más similares a la pregunta por distancia coseno.

    pgvector expone `<=>` como distancia coseno (0 = idéntico, 2 = opuesto);
    la convertimos a similitud (1 - distancia) para que el umbral de corte en
    `Settings.min_similarity` sea intuitivo (más alto = más relevante).
    """
    query_embedding = embed_query(question)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance)
        .limit(top_k)
    )
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(
            label=chunk.label,
            content=chunk.content,
            document_title=doc.title,
            url=doc.url,
            similarity=1 - distance_value,
        )
        for chunk, doc, distance_value in rows
    ]
