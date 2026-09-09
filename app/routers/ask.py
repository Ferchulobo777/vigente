from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.generation import GenerationError, generate_answer
from app.retrieval import retrieve
from app.schemas import AskRequest, AskResponse, Citation

router = APIRouter()

_NO_SOURCE_ANSWER = (
    "No encontré una fuente lo bastante específica en la normativa de Monotributo cargada "
    "para responder esto con confianza. Reformulá la pregunta o consultá directamente a ARCA."
)


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    settings = get_settings()
    chunks = retrieve(db, payload.question, top_k=settings.top_k)
    relevant = [c for c in chunks if c.similarity >= settings.min_similarity]

    if not relevant:
        return AskResponse(answer=_NO_SOURCE_ANSWER, citations=[], grounded=False)

    try:
        answer = generate_answer(payload.question, relevant)
    except GenerationError as exc:
        raise HTTPException(
            status_code=503,
            detail="El servicio de generación no está disponible en este momento. Intentá de nuevo más tarde.",
        ) from exc
    citations = [
        Citation(label=c.label, document_title=c.document_title, url=c.url, similarity=round(c.similarity, 3))
        for c in relevant
    ]
    return AskResponse(answer=answer, citations=citations, grounded=True)
