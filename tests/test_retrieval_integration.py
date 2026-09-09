"""Test de integración real: levanta Postgres+pgvector con Testcontainers,
inserta chunks con embeddings reales (sentence-transformers, sin mock) y
verifica que la búsqueda por similitud devuelve el fragmento correcto.

Esto es lo único que puede detectar un bug real de la query pgvector
(`<=>` mal usado, dimensión de vector incorrecta, etc.) — un mock de
retrieval nunca lo hubiera encontrado.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from app.db import Base
from app.embeddings import embed_passage
from app.models import Chunk, Document
from app.retrieval import retrieve


@pytest.fixture(scope="module")
def db_session():
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as pg:
        engine = create_engine(pg.get_connection_url())
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            doc = Document(
                source_id="test-doc",
                title="Resolución de prueba",
                url="https://example.com/norma",
            )
            session.add(doc)
            session.flush()

            texts = {
                "Artículo 4°": "Para adherirse al monotributo hay que solicitar la CUIT.",
                "Artículo 15°": "Los parámetros de categorización incluyen superficie y energía.",
                "Categoría F": "La categoría F tiene un tope de ingresos brutos anuales alto.",
            }
            for label, content in texts.items():
                session.add(
                    Chunk(document_id=doc.id, label=label, content=content, embedding=embed_passage(content))
                )
            session.commit()
            yield session


def test_retrieve_finds_the_semantically_closest_chunk(db_session):
    results = retrieve(db_session, "¿Qué trámite necesito para darme de alta en monotributo?", top_k=3)

    assert len(results) == 3
    assert results[0].label == "Artículo 4°"
    assert results[0].similarity > results[1].similarity


def test_retrieve_similarity_is_bounded_between_0_and_1(db_session):
    results = retrieve(db_session, "categorización por superficie", top_k=3)

    for r in results:
        assert 0.0 <= r.similarity <= 1.0
