from fastapi import FastAPI

from app.routers import ask, health

app = FastAPI(
    title="Vigente",
    description=(
        "Asistente de Monotributo con citas verificables — cada respuesta cita el artículo "
        "o fuente exacta, y se niega a responder si no hay una fuente suficientemente relevante."
    ),
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(ask.router, prefix="/api/v1")
