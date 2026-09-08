"""Esquemas del dominio académico (T-005, T-006, T-010).

Ningún esquema de entrada expone `institucion_id`: el tenant se deriva del token
(ADR-003). Que no exista el campo hace imposible falsearlo desde el cliente.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import EstadoFicha, EstadoGuia, EstadoInscripcion
from app.schemas.comun import EsquemaBase

# --------------------------------------------------------------------------- #
# Fichas
# --------------------------------------------------------------------------- #


class FichaCrear(BaseModel):
    codigo: str = Field(min_length=3, max_length=20)
    nombre: str = Field(min_length=3, max_length=200)
    programa: str = Field(min_length=2, max_length=120)
    trimestre: str = Field(min_length=4, max_length=10, examples=["2026-2"])


class FichaActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=200)
    programa: str | None = Field(default=None, min_length=2, max_length=120)
    trimestre: str | None = Field(default=None, min_length=4, max_length=10)


class FichaPublica(EsquemaBase):
    id: uuid.UUID
    codigo: str
    nombre: str
    programa: str
    trimestre: str
    estado: EstadoFicha
    docente_id: uuid.UUID


# --------------------------------------------------------------------------- #
# Inscripciones
# --------------------------------------------------------------------------- #


class InscripcionCrear(BaseModel):
    email: EmailStr
    nombre: str | None = Field(default=None, max_length=150)


class InscripcionPublica(EsquemaBase):
    id: uuid.UUID
    ficha_id: uuid.UUID
    aprendiz_id: uuid.UUID
    estado: EstadoInscripcion


class ResumenCargaMasiva(BaseModel):
    creadas: int
    duplicadas: int
    errores: list[dict[str, str | int]]


# --------------------------------------------------------------------------- #
# Guías
# --------------------------------------------------------------------------- #


class GuiaCrear(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str | None = None
    # Markdown. Es lo que ancla las preguntas del agente al temario real.
    contexto_tecnico: str | None = None
    num_preguntas: int = Field(default=8, ge=3, le=20)
    abre_en: datetime | None = None
    cierra_en: datetime | None = None

    @model_validator(mode="after")
    def _ventana_coherente(self) -> "GuiaCrear":
        if self.abre_en and self.cierra_en and self.cierra_en <= self.abre_en:
            raise ValueError("`cierra_en` debe ser posterior a `abre_en`")
        return self


class GuiaActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = None
    contexto_tecnico: str | None = None
    num_preguntas: int | None = Field(default=None, ge=3, le=20)
    abre_en: datetime | None = None
    cierra_en: datetime | None = None


class GuiaPublica(EsquemaBase):
    id: uuid.UUID
    ficha_id: uuid.UUID
    titulo: str
    descripcion: str | None
    num_preguntas: int
    estado: EstadoGuia
    abre_en: datetime | None
    cierra_en: datetime | None


class GuiaDetalle(GuiaPublica):
    contexto_tecnico: str | None
    rubrica: "RubricaPublica | None" = None


# --------------------------------------------------------------------------- #
# Rúbricas
# --------------------------------------------------------------------------- #


class CriterioCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = None
    peso: int = Field(ge=1, le=100)


class RubricaCrear(BaseModel):
    umbral_aprobacion: int = Field(default=60, ge=0, le=100)
    criterios: list[CriterioCrear] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def _pesos_suman_cien(self) -> "RubricaCrear":
        """Invariante de negocio: los pesos deben sumar exactamente 100.

        Se valida aquí y no en la base de datos para devolver un 422 con un
        mensaje que le sirva al instructor.
        """
        total = sum(c.peso for c in self.criterios)
        if total != 100:
            raise ValueError(f"Los pesos de los criterios deben sumar 100. Suma actual: {total}.")
        nombres = [c.nombre.strip().lower() for c in self.criterios]
        if len(set(nombres)) != len(nombres):
            raise ValueError("Hay criterios con el mismo nombre")
        return self


class CriterioPublico(EsquemaBase):
    id: uuid.UUID
    nombre: str
    descripcion: str | None
    peso: int
    orden: int


class RubricaPublica(EsquemaBase):
    id: uuid.UUID
    guia_id: uuid.UUID
    umbral_aprobacion: int
    criterios: list[CriterioPublico]


GuiaDetalle.model_rebuild()
