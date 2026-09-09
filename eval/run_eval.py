"""Evalúa la calidad del retrieval (no la generación — eso requiere créditos
de la API de Claude) contra `dataset.jsonl`: para cada pregunta de
referencia, ¿el fragmento correcto aparece entre los top-k recuperados?

Esto es Recall@k, la métrica estándar para medir un pipeline de retrieval de
RAG antes de gastar en la parte de generación. Un score bajo acá significa
que el problema es de embeddings/chunking, no del LLM — no tiene sentido
seguir iterando el prompt de generación si el retrieval ya está fallando.

Uso:
    python -m eval.run_eval
"""

import json
from pathlib import Path

from app.config import get_settings
from app.db import SessionLocal
from app.retrieval import retrieve

_DATASET_PATH = Path(__file__).parent / "dataset.jsonl"


def load_dataset() -> list[dict]:
    with _DATASET_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    settings = get_settings()
    dataset = load_dataset()
    db = SessionLocal()

    hits = 0
    print(f"{'Pregunta':<70} {'Esperado':<15} {'Resultado':<10}")
    print("-" * 100)
    try:
        for item in dataset:
            results = retrieve(db, item["question"], top_k=settings.top_k)
            found_labels = [r.label for r in results]
            hit = item["expected_label"] in found_labels
            hits += hit
            status = "OK" if hit else "MISS"
            print(f"{item['question']:<70} {item['expected_label']:<15} {status:<10}")
    finally:
        db.close()

    total = len(dataset)
    print("-" * 100)
    print(f"Recall@{settings.top_k}: {hits}/{total} ({100 * hits / total:.0f}%)")


if __name__ == "__main__":
    main()
