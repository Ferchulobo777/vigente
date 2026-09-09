import datetime as dt

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.db import Base

_DIM = get_settings().embedding_dim


class Document(Base):
    """Una norma o fuente de datos completa (ej. RG 4309/2018, tabla de categorías)."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[dt.date | None]
    fetched_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Un fragmento citable de un documento (un artículo, una fila de tabla)."""

    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "label", name="uq_chunk_document_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text)  # ej. "Artículo 4°" o "Categoría F"
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(_DIM))

    document: Mapped[Document] = relationship(back_populates="chunks")
