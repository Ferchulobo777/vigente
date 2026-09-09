from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import ask, health

app = FastAPI(
    title="Vigente",
    description=(
        "Asistente de Monotributo con citas verificables — cada respuesta cita el artículo "
        "o fuente exacta, y se niega a responder si no hay una fuente suficientemente relevante."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().allowed_origins.split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(ask.router, prefix="/api/v1")
