<div align="center">

# ⚖️ Vigente

**El asistente de Monotributo que nunca inventa un dato.**
RAG (Retrieval-Augmented Generation) sobre normativa real de InfoLeg: cada respuesta cita el artículo exacto de donde sale, y se niega a responder si no encuentra una fuente lo bastante relevante.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Claude](https://img.shields.io/badge/Claude-Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![Testcontainers](https://img.shields.io/badge/Tested_with-Testcontainers-2496ED?style=for-the-badge&logo=testcontainers&logoColor=white)](https://testcontainers.com)

**[🔗 Ver API en vivo](#)** &middot; **[📖 Swagger UI](#)**

</div>

<br />

Construido como pieza de portfolio para demostrar el patrón de IA más
demandado en despliegues empresariales de 2026: RAG con grounding real, no
"chateá con tu PDF". El dominio (Monotributo argentino) se eligió a
propósito acotado — ver [`CLAUDE.md`](./CLAUDE.md) para el porqué.

Frontend (PWA instalable, SvelteKit): [github.com/Ferchulobo777/vigente-web](https://github.com/Ferchulobo777/vigente-web).

## Índice

- [Qué tiene](#qué-tiene)
- [Cómo responde sin inventar](#cómo-responde-sin-inventar)
- [Fuentes de datos](#fuentes-de-datos)
- [Stack](#stack)
- [Empezar](#empezar)
- [Evaluación](#evaluación)
- [Límites conocidos](#límites-conocidos-a-propósito-no-por-descuido)

## Qué tiene

- **Ingesta real desde InfoLeg**, no un dataset preparado a mano: el cliente
  descarga y parsea el HTML real de la Resolución General 4309/2018
  (Monotributo), decodificando correctamente su encoding ISO-8859-1 y
  extrayendo cada uno de sus 100+ artículos como un fragmento citable
  independiente.
- **Tabla de categorías vigente** capturada de la fuente oficial de ARCA,
  con su fecha de vigencia registrada — no un valor hardcodeado sin origen.
- **Embeddings multilingües locales** (`intfloat/multilingual-e5-small`, sin
  API key) + búsqueda por distancia coseno en pgvector.
- **Generación grounded con Claude**: el prompt exige citar cada afirmación
  con la etiqueta exacta de su fuente, y prohíbe completar con conocimiento
  general fuera de los fragmentos recuperados.
- **Rechazo explícito sin fuente suficiente**: si nada supera el umbral de
  similitud, la API responde que no sabe — sin llamar siquiera al LLM.
- **Suite de evaluación de retrieval** (`eval/`) con Recall@k contra un
  dataset de preguntas de referencia.
- **Tests en 3 niveles**: unitario (parser de InfoLeg contra HTML real
  capturado), integración con Testcontainers (pgvector real, embeddings
  reales, sin mocks) y de contrato HTTP (`/ask` con retrieval mockeado).

## Cómo responde sin inventar

```
pregunta → embedding local → búsqueda coseno en pgvector → top-k fragmentos
                                                                  │
                                              ¿algún fragmento supera el
                                              umbral de similitud?
                                                    │           │
                                                   no           sí
                                                    │           │
                                     "no sé, consultá         Claude genera la
                                      a ARCA" (sin LLM)        respuesta citando
                                                                cada fragmento
```

## Fuentes de datos

| Fuente | Contenido | Licencia |
| --- | --- | --- |
| [RG 4309/2018 (InfoLeg)](https://servicios.infoleg.gob.ar/infolegInternet/anexos/310000-314999/314485/norma.htm) | Texto completo del Régimen Simplificado | CC-BY 2.5 Argentina |
| [Categorías vigentes (ARCA)](https://www.afip.gob.ar/monotributo/categorias.asp) | Topes de facturación y cuotas por categoría | Fuente pública oficial |

## Stack

| Categoría | Tecnología |
| --- | --- |
| API | FastAPI, Pydantic v2 |
| Persistencia | PostgreSQL + pgvector, SQLAlchemy 2 |
| Embeddings | sentence-transformers (`multilingual-e5-small`, local) |
| Generación | Claude (Anthropic) |
| Ingesta | httpx + parser propio para el HTML de InfoLeg |
| Testing | pytest, Testcontainers |
| Deploy | Docker, Render (Blueprint) + Neon (Postgres serverless) |

## Empezar

```bash
python -m venv .venv && .venv/Scripts/activate  # o source .venv/bin/activate
pip install -e ".[dev]"

docker compose up -d db           # Postgres + pgvector en :5433
python -m ingest.embed_and_load    # carga el corpus real (~1 min)

cp .env.example .env               # completar ANTHROPIC_API_KEY
uvicorn app.main:app --reload

pytest                              # incluye integración real con Testcontainers
```

## Evaluación

```bash
python -m eval.run_eval
```

Mide Recall@k del retrieval contra `eval/dataset.jsonl` — preguntas reales
con la cita exacta que se espera encontrar. Un score bajo acá señala un
problema de embeddings/chunking, no de la generación.

## Límites conocidos (a propósito, no por descuido)

- Corpus acotado a Monotributo — no cubre IVA, Ganancias ni Ingresos Brutos.
  Ver [`CLAUDE.md`](./CLAUDE.md).
- La tabla de categorías requiere actualización manual cada vez que ARCA
  ajusta los montos (~2 veces al año) — no hay scraping automático todavía.
- **Preguntas comparativas/superlativas** ("¿cuál es la categoría con el
  tope más alto?") no son resolubles con similitud vectorial pura — medido,
  no supuesto: ver "Límites conocidos del retrieval" en
  [`CLAUDE.md`](./CLAUDE.md).
- **Artículos densos con muchos incisos pierden ranking** cuando la
  pregunta no comparte vocabulario literal con el texto legal — Recall@8
  actual contra `eval/dataset.jsonl`, no 100%. Detalle y próximo paso
  (sub-chunking por inciso) en `CLAUDE.md`.
- La evaluación mide Recall@k del retrieval, no la fidelidad de la
  respuesta generada (eso requiere correr generación real contra el
  dataset, con costo de API) — documentado como próximo paso.
- Sin autenticación ni rate limiting — de uso público y bajo riesgo por
  ahora.

## Créditos

<div align="center">
<sub>Diseñado y desarrollado por <a href="https://github.com/Ferchulobo777">Fernando Rodríguez</a></sub>
</div>

Datos de InfoLeg bajo licencia Creative Commons Reconocimiento 2.5
Argentina. Esta herramienta no ofrece asesoramiento impositivo profesional —
la información se brinda "tal cual". Proyecto personal, sin fines
comerciales.
