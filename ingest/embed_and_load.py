"""Pipeline de ingesta: descarga las fuentes reales, las divide en chunks
citables, calcula sus embeddings y las guarda en Postgres/pgvector.

Uso:
    python -m ingest.embed_and_load
"""

import logging

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.embeddings import embed_passage
from app.models import Chunk, Document
from ingest.infoleg_client import extract_articles, fetch_raw_html
from ingest.sources import (
    INFOLEG_SOURCES,
    MONOTRIBUTO_SCALE,
    MONOTRIBUTO_SCALE_PUBLISHED_AT,
    MONOTRIBUTO_SCALE_SOURCE_ID,
    MONOTRIBUTO_SCALE_TITLE,
    MONOTRIBUTO_SCALE_URL,
    scale_row_to_chunk_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _upsert_document(db: Session, source_id: str, title: str, url: str, published_at) -> Document:
    stmt = (
        pg_insert(Document)
        .values(source_id=source_id, title=title, url=url, published_at=published_at)
        .on_conflict_do_update(
            index_elements=[Document.source_id],
            set_={"title": title, "url": url, "published_at": published_at},
        )
        .returning(Document.id)
    )
    doc_id = db.execute(stmt).scalar_one()
    db.commit()
    return db.get(Document, doc_id)


def load_infoleg_sources(db: Session) -> int:
    total = 0
    for source in INFOLEG_SOURCES:
        log.info("Descargando %s (%s)", source.source_id, source.url)
        raw_html = fetch_raw_html(source.url)
        articles = extract_articles(raw_html)
        log.info("  -> %d artículos extraídos", len(articles))

        document = _upsert_document(db, source.source_id, source.title, source.url, source.published_at)

        for article in articles:
            embedding = embed_passage(article.content)
            stmt = (
                pg_insert(Chunk)
                .values(
                    document_id=document.id,
                    label=article.label,
                    content=article.content,
                    embedding=embedding,
                )
                .on_conflict_do_update(
                    index_elements=[Chunk.document_id, Chunk.label],
                    set_={"content": article.content, "embedding": embedding},
                )
            )
            db.execute(stmt)
            total += 1
        db.commit()
    return total


def load_monotributo_scale(db: Session) -> int:
    document = _upsert_document(
        db,
        MONOTRIBUTO_SCALE_SOURCE_ID,
        MONOTRIBUTO_SCALE_TITLE,
        MONOTRIBUTO_SCALE_URL,
        MONOTRIBUTO_SCALE_PUBLISHED_AT,
    )
    count = 0
    for row in MONOTRIBUTO_SCALE:
        text = scale_row_to_chunk_text(row)
        embedding = embed_passage(text)
        label = f"Categoría {row.category}"
        stmt = (
            pg_insert(Chunk)
            .values(document_id=document.id, label=label, content=text, embedding=embedding)
            .on_conflict_do_update(
                index_elements=[Chunk.document_id, Chunk.label],
                set_={"content": text, "embedding": embedding},
            )
        )
        db.execute(stmt)
        count += 1
    db.commit()
    return count


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        n1 = load_infoleg_sources(db)
        n2 = load_monotributo_scale(db)
        log.info("Listo: %d artículos de InfoLeg + %d filas de escala = %d chunks totales", n1, n2, n1 + n2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
