import anthropic

from app.config import get_settings
from app.retrieval import RetrievedChunk

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
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = _build_context(chunks)

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
    return "".join(block.text for block in message.content if block.type == "text")
