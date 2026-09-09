from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://vigente:vigente@localhost:5433/vigente"
    anthropic_api_key: str = ""
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384

    # Umbral de similitud coseno por debajo del cual no hay fuente suficientemente
    # relevante y la API debe negarse a responder en vez de inventar. Calibrado
    # contra el dataset de evaluación en eval/dataset.jsonl — ver CLAUDE.md.
    min_similarity: float = 0.72
    # Subido de 5 a 8 tras medir Recall@k contra eval/dataset.jsonl: varios
    # artículos relevantes rankean entre el puesto 6 y 8 cuando la pregunta
    # no comparte vocabulario literal con el texto legal (ver CLAUDE.md,
    # "Límites conocidos del retrieval").
    top_k: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
