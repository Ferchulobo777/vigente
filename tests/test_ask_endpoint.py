from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.retrieval import RetrievedChunk

client = TestClient(app)

_GOOD_CHUNK = RetrievedChunk(
    label="Artículo 4°",
    content="Los pequeños contribuyentes deberán solicitar CUIT antes de adherir.",
    document_title="Resolución General 4309/2018",
    url="https://servicios.infoleg.gob.ar/infolegInternet/anexos/310000-314999/314485/norma.htm",
    similarity=0.91,
)

_WEAK_CHUNK = RetrievedChunk(
    label="Artículo 99°",
    content="Algo apenas relacionado.",
    document_title="Resolución General 4309/2018",
    url="https://example.com",
    similarity=0.40,
)


def test_ask_refuses_when_no_chunk_passes_the_similarity_threshold():
    """Si nada supera el umbral de similitud, la API debe negarse a responder
    en vez de inventar — es la regla más importante de todo el proyecto."""
    with patch("app.routers.ask.retrieve", return_value=[_WEAK_CHUNK]):
        response = client.post("/api/v1/ask", json={"question": "¿Cuánto pago en categoría F?"})

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["citations"] == []


def test_ask_returns_grounded_answer_with_citations_when_relevant_chunk_found():
    with (
        patch("app.routers.ask.retrieve", return_value=[_GOOD_CHUNK]),
        patch("app.routers.ask.generate_answer", return_value="Debés solicitar CUIT [Artículo 4°]."),
    ):
        response = client.post("/api/v1/ask", json={"question": "¿Qué necesito para adherirme?"})

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert len(body["citations"]) == 1
    assert body["citations"][0]["label"] == "Artículo 4°"
    assert "Artículo 4°" in body["answer"]


def test_ask_rejects_questions_shorter_than_3_characters():
    response = client.post("/api/v1/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_ask_response_always_includes_the_disclaimer():
    with patch("app.routers.ask.retrieve", return_value=[_WEAK_CHUNK]):
        response = client.post("/api/v1/ask", json={"question": "¿Cuánto pago en categoría F?"})

    assert "no es asesoramiento" in response.json()["disclaimer"].lower() or (
        "orientación" in response.json()["disclaimer"].lower()
    )
