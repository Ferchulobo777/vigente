FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser ingest ./ingest

RUN pip install --no-cache-dir --user .

# Descarga el modelo de embeddings en build time, no en el primer request —
# evita que el primer usuario espere ~1min mientras se baja el modelo.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('intfloat/multilingual-e5-small')"

ENV PATH="/home/appuser/.local/bin:${PATH}"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
