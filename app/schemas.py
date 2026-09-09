from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    label: str
    document_title: str
    url: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
    disclaimer: str = (
        "Esta respuesta es orientación general basada en normativa vigente de Monotributo, "
        "no asesoramiento impositivo profesional. Verificá siempre contra la fuente citada "
        "antes de tomar una decisión."
    )
