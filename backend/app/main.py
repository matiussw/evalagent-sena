"""Ensamblado de la aplicación FastAPI."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import academico, auth, salud, sesiones, ws
from app.core.config import get_settings
from app.services.errores import ErrorDominio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
_settings = get_settings()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    from app.services import tts

    motor = tts.motor_activo()
    logger.info("Motor TTS: %s", motor.describir())
    if motor.nombre == "ninguno":
        logger.warning("Sin motor TTS: las sustentaciones funcionarán en modo solo texto")
    yield


app = FastAPI(
    title=_settings.APP_NAME,
    version=_settings.APP_VERSION,
    description=(
        "Plataforma de sustentación oral asistida por IA para el programa ADSO "
        "del SENA. Toda la IA corre en local (ADR-001) y ninguna nota se publica "
        "sin confirmación de un instructor (ADR-006)."
    ),
    lifespan=ciclo_de_vida,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# T-013 (deuda D6): lista blanca por entorno. La configuración aborta el
# arranque si alguien intenta poner `*` junto a credenciales.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_lista,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ErrorDominio)
async def manejar_error_dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
    """Traduce los errores de negocio a respuestas RFC 7807.

    Los servicios lanzan excepciones de dominio sin saber nada de HTTP; la
    traducción vive aquí.
    """
    return JSONResponse(
        status_code=exc.estado,
        media_type="application/problem+json",
        content={
            "type": f"https://evalagent.sena.edu.co/errores/{exc.tipo}",
            "title": exc.titulo,
            "status": exc.estado,
            "detail": exc.detalle,
            "instance": str(request.url.path),
        },
    )


PREFIJO = "/api/v1"
app.include_router(salud.router, prefix=PREFIJO)
app.include_router(auth.router, prefix=PREFIJO)
app.include_router(academico.router, prefix=PREFIJO)
app.include_router(sesiones.router, prefix=PREFIJO)
app.include_router(ws.router, prefix=PREFIJO)


@app.get("/", include_in_schema=False)
async def raiz() -> dict:
    return {
        "nombre": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
        "documentacion": "/docs",
    }
