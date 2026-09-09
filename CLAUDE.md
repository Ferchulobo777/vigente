# Vigente

Asistente de Monotributo con citas verificables. Cada respuesta cita el
artículo o fuente exacta de donde sale, y se niega a responder si no hay una
fuente suficientemente relevante — es un proyecto de portfolio construido
para demostrar el patrón RAG (Retrieval-Augmented Generation) con grounding
real, no un producto en producción con usuarios reales.

## Por qué existe

Ver `PORTFOLIO 2026/02 Estrategia y Contenido/Plan Nivel Senior 2026.md` en
la bóveda de Obsidian del portfolio: el diagnóstico fue que ningún proyecto
público mostraba IA aplicada de verdad (usar Claude Code para escribir
código no cuenta como "proyecto de IA"), y RAG es el patrón más demandado en
2026 en despliegues empresariales de IA.

## Alcance deliberadamente acotado: Monotributo, no "toda la normativa ARCA"

"Normativa ARCA completa" es un corpus enorme y en constante cambio (todos
los impuestos, todas las provincias de Ingresos Brutos, actualizaciones
diarias). Prometer cobertura de eso y no poder mantenerlo actualizado sería
peor que no tener el proyecto. El Régimen Simplificado (Monotributo) es:

- Un tema acotado y estable (una norma principal + una tabla de montos que
  cambia ~2 veces por año).
- El de mayor volumen de consultas reales entre freelancers y pymes.
- Suficiente para demostrar el patrón completo (ingesta real, chunking,
  embeddings, retrieval, generación con grounding, rechazo sin fuente,
  evaluación) sin la carga de mantenimiento de un corpus legal completo.

Ampliar el corpus a futuro es agregar entradas a `ingest/sources.py`, no
rediseñar nada.

## Fuentes de datos (verificadas a mano, no supuestas)

- **RG 4309/2018 (AFIP)** — texto completo real desde InfoLeg
  (`servicios.infoleg.gob.ar`), CC-BY 2.5 Argentina. La página de InfoLeg NO
  tiene estructura semántica (sin `<article>`/`<section>`, todo separado por
  `<br>`) y está codificada en **ISO-8859-1, no UTF-8** — confirmado
  descargando la página real antes de escribir el parser. Los artículos se encabezan como `ARTÍCULO 4°.-` (con el símbolo °) o `ARTÍCULO 10.-` (sin él,
  para números de dos dígitos) — el patrón regex en `ingest/infoleg_client.py`
  contempla ambos casos; ver `tests/test_infoleg_client.py`.
- **Tabla de categorías vigente** — capturada directamente de
  `afip.gob.ar/monotributo/categorias.asp` (la fuente oficial de ARCA, no un
  artículo periodístico). Se actualiza por resolución ~2 veces al año; la
  fecha de vigencia queda registrada en `MONOTRIBUTO_SCALE_PUBLISHED_AT`.

## Arquitectura

```
ingest/         pipeline offline: fetch -> chunk -> embed -> Postgres
  infoleg_client.py   descarga y parsea el HTML real de InfoLeg
  sources.py          lista curada de fuentes (agregar acá para ampliar el corpus)
  embed_and_load.py   orquesta todo, upsert idempotente por (document, label)

app/            API online: recibe una pregunta, devuelve una respuesta citada
  retrieval.py        embedding de la pregunta + búsqueda por distancia coseno en pgvector
  generation.py       llamada a Claude con prompt que exige citar o admitir que no sabe
  routers/ask.py       corta la generación si nada supera `min_similarity` — no pasa por el LLM
```

## Decisiones de arquitectura (y por qué)

- **Embeddings locales (sentence-transformers), generación con Claude.**
  Anthropic no ofrece una API de embeddings — solo generación de texto. En
  vez de contratar un segundo proveedor (OpenAI) solo para embeddings, se usa
  `intfloat/multilingual-e5-small` local: gratis, sin key, corre en CPU, y
  tiene buen desempeño en español. Los modelos E5 requieren prefijar el texto
  con `"query: "` o `"passage: "` según sea pregunta o fragmento indexado —
  omitir esto degrada la similitud notablemente (ver `app/embeddings.py`).
- **El "no sé" es una feature, no un caso de error.** `min_similarity` en
  `app/config.py` corta la respuesta ANTES de llamar al LLM si nada es lo
  bastante relevante — la API nunca le pide a Claude que responda sobre
  fragmentos irrelevantes con la esperanza de que "sepa que no sabe". El
  umbral (0.72) es un punto de partida razonable, no un valor mágico —
  recalibrar contra `eval/dataset.jsonl` a medida que el corpus crezca.
- **Solo se indexan los artículos operativos, no el VISTO/CONSIDERANDO.**
  El preámbulo de una resolución (sus fundamentos) no es texto con fuerza
  normativa — indexarlo arriesga que el modelo cite un "considerando" como
  si fuera una obligación real.
- **Sin Alembic/migraciones versionadas.** A diferencia de `indexar-api`
  (que sí las tiene y es donde se demuestra esa disciplina), acá `create_all`
  alcanza: el schema es simple (2 tablas) y el foco de este proyecto es el
  patrón RAG, no repetir la misma señal de "sé versionar un schema" dos
  veces en el portfolio.

## Límites conocidos del retrieval (medidos, no supuestos)

Corriendo `eval/run_eval.py` contra el corpus real, Recall@5 dio 70% (7/10).
Auditando los 3 misses uno por uno (no descartados a ojo):

- **Artículos densos con incisos a)/b)/c) pierden ranking** cuando la
  pregunta no comparte vocabulario literal con el texto legal. El
  Artículo 4° (trámites previos a la adhesión: CUIT, datos biométricos,
  domicilio fiscal electrónico) es genuinamente relevante para "¿qué
  trámite tengo que hacer antes de darme de alta?", pero rankeaba #18/115
  — cada inciso agrega vocabulario burocrático (números de Resolución,
  formularios) que diluye la señal semántica del artículo completo. Subir
  `top_k` de 5 a 8 (ver `app/config.py`) mitiga parte de esto; una mejora
  real de fondo sería sub-chunkear artículos con incisos en vez de
  embeber el artículo entero como una sola unidad — no implementado
  todavía, queda como próximo paso documentado.
- **Las preguntas superlativas/comparativas ("¿cuál es la categoría con el
  tope más alto?") no son resolubles con similitud vectorial pura.** Las
  11 filas de la tabla de categorías son textualmente casi idénticas
  (mismo template, solo cambian los montos), así que todas quedan a
  distancia coseno muy similar de cualquier pregunta sobre "categoría" —
  el embedding no puede razonar sobre cuál valor es mayor. Esto no es un
  bug de chunking ni de umbral: es una limitación estructural de RAG
  basado en similitud semántica. La solución real (fuera de alcance acá)
  sería detectar el patrón de pregunta agregada/comparativa y resolverla
  con una query estructurada sobre los datos, no con retrieval semántico.

## Gotchas encontrados

- **El test de integración con Testcontainers no corre en este entorno de
  desarrollo** (Windows sin Docker Desktop, solo Docker Engine dentro de
  WSL) — `docker.errors.DockerException` al no encontrar
  `\\.\pipe\docker_engine`. No es un defecto del código: correrá normal en
  cualquier CI con Docker disponible (Docker-in-Docker) o ejecutando pytest
  desde dentro de WSL. Lo que ese test verifica (retrieval real contra
  Postgres+pgvector, sin mocks) ya se validó manualmente corriendo el
  pipeline de ingesta completo contra un proyecto real de Neon — 104
  artículos + 11 filas de escala, Recall@8 medido en 80% contra
  `eval/dataset.jsonl` — una validación más fuerte que un Postgres efímero.
- httpx no decodifica ISO-8859-1 automáticamente si el servidor no manda un
  header `Content-Type: charset=...` explícito (InfoLeg solo lo declara en
  un `<meta>` HTML, que httpx no inspecciona) — hay que decodificar
  `response.content` a mano con `.decode("iso-8859-1")`. Usar
  `response.text` directamente corrompe todas las tildes y la "ñ".

## Correr en local

```bash
python -m venv .venv && .venv/Scripts/activate  # o source .venv/bin/activate en Linux/Mac
pip install -e ".[dev]"

docker compose up -d db          # Postgres + pgvector en :5433
python -m ingest.embed_and_load  # carga el corpus real (tarda ~1 min, descarga el modelo de embeddings la 1ª vez)

cp .env.example .env             # completar ANTHROPIC_API_KEY antes de levantar la API
uvicorn app.main:app --reload

pytest                            # incluye el test de integración con Testcontainers (necesita Docker)
```
