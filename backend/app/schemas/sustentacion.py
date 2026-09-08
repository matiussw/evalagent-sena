"""Esquemas de sustentación y revisión (T-007, T-011)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EstadoSesion, RolTurno
from app.schemas.comun import EsquemaBase


class SesionCrear(BaseModel):
    guia_id: uuid.UUID
    # Sin consentimiento no se crea la sesión. Requisito legal, no una casilla
    # de cortesía (Ley 1581/2012).
    consentimiento_aceptado: bool

    @field_validator("consentimiento_aceptado")
    @classmethod
    def _debe_aceptar(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Debes aceptar el aviso de tratamiento de datos para sustentar")
        return v


class TurnoPublico(EsquemaBase):
    orden: int
    rol: RolTurno
    contenido: str
    creado_en: datetime


class SesionIniciada(BaseModel):
    """Respuesta al crear una sesión. Incluye el ticket del canal de voz."""

    id: uuid.UUID
    estado: EstadoSesion
    guia_titulo: str
    num_preguntas: int
    rubrica_congelada: dict
    ws_ticket: str
    ws_url: str


class SesionPublica(EsquemaBase):
    id: uuid.UUID
    guia_id: uuid.UUID
    aprendiz_id: uuid.UUID
    estado: EstadoSesion
    preguntas_respondidas: int
    iniciada_en: datetime | None
    finalizada_en: datetime | None


class SesionDetalle(SesionPublica):
    rubrica_congelada: dict
    turnos: list[TurnoPublico]


# --------------------------------------------------------------------------- #
# Revisión (ADR-006)
# --------------------------------------------------------------------------- #


class RevisionPendiente(BaseModel):
    """Lo que ve el instructor antes de confirmar.

    Es el único lugar donde se exponen las puntuaciones propuestas por el
    agente: al aprendiz no se le muestran nunca.
    """

    sesion_id: uuid.UUID
    aprendiz: str
    guia_titulo: str
    estado: EstadoSesion
    rubrica_congelada: dict
    puntuaciones_agente: dict | None
    nota_propuesta: float | None
    turnos: list[TurnoPublico]


class RevisionConfirmar(BaseModel):
    puntuaciones_finales: dict[str, int] = Field(min_length=1)
    retroalimentacion: str | None = Field(default=None, max_length=4000)

    @field_validator("puntuaciones_finales")
    @classmethod
    def _rango_valido(cls, v: dict[str, int]) -> dict[str, int]:
        fuera = {k: p for k, p in v.items() if not 0 <= p <= 10}
        if fuera:
            raise ValueError(f"Las puntuaciones van de 0 a 10. Fuera de rango: {fuera}")
        return v


class RevisionConfirmada(BaseModel):
    sesion_id: uuid.UUID
    estado: EstadoSesion
    nota_final: float
    aprobado: bool
    revisor_id: uuid.UUID
    confirmada_en: datetime
    # Evidencia de supervisión humana efectiva. Alimenta los KPIs K4 y K5.
    diferencias_con_agente: dict[str, dict[str, int]]


class ResultadoAprendiz(BaseModel):
    """Lo que ve el aprendiz.

    Mientras la sesión no esté CALIFICADA, `nota_final` y el desglose van a
    `None` y solo se devuelve el mensaje de estado (ADR-006).
    """

    sesion_id: uuid.UUID
    guia_titulo: str
    estado: EstadoSesion
    mensaje: str | None = None
    nota_final: float | None = None
    aprobado: bool | None = None
    desglose: dict[str, int] | None = None
    retroalimentacion: str | None = None
