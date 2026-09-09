import anthropic

from app.config import get_settings
from app.retrieval import RetrievedChunk


class GenerationError(Exception):
    """La llamada a Claude falló (sin API key, sin crédito, timeout, etc.).

    Separado de las excepciones crudas de `anthropic` para que el router
    pueda traducirlo a un 503 con mensaje claro, en vez de un 500 con un
    stack trace de la librería del proveedor — el mismo principio de "ningún
    endpoint devuelve un stack trace crudo" que se aplica en indexar-api.
    """

_SYSTEM_PROMPT = """Sos un asistente que responde preguntas sobre el Régimen Simplificado \
para Pequeños Contribuyentes (Monotributo) de Argentina, EXCLUSIVAMENTE con la información \
de las fuentes provistas abajo.

Reglas estrictas:
1. Nunca afirmes un dato (monto, plazo, requisito) que no esté literalmente en las fuentes.
2. Citá cada afirmación con la etiqueta de la fuente entre corchetes, ej. [Artículo 4°].
3. Si las fuentes no alcanzan para responder con certeza, decilo explícitamente en vez de \
completar con conocimiento general — es preferible una respuesta incompleta a una incorrecta.
4. No des asesoramiento impositivo personalizado ("deberías", "te conviene") — describí lo \
que dice la norma y dejá la decisión al usuario.
"""


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"### Fuente: {c.document_title} — {c.label}\n{c.content}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise GenerationError("ANTHROPIC_API_KEY no está configurada.")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = _build_context(chunks)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=700,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"FUENTES:\n\n{context}\n\nPREGUNTA: {question}",
                }
            ],
        )
    except anthropic.APIError as exc:
        raise GenerationError(f"La API de Claude no respondió correctamente: {exc}") from exc

    return "".join(block.text for block in message.content if block.type == "text")
