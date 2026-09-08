"""Dominio académico: Ficha, Inscripción, Guía y Rúbrica (T-005, T-006, T-010)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ModeloBase
from app.models.enums import EstadoFicha, EstadoGuia, EstadoInscripcion
from app.models.identidad import Usuario

if TYPE_CHECKING:
    from app.models.sustentacion import Sesion


class Ficha(ModeloBase):
    """Curso/clase del SENA. Equivale a una clase de Google Classroom."""

    __tablename__ = "fichas"
    __table_args__ = (
        # El mismo código puede repetirse entre centros, pero no dentro de uno.
        UniqueConstraint("institucion_id", "codigo", name="uq_ficha_institucion_codigo"),
        Index("idx_ficha_docente_estado", "docente_id", "estado"),
    )

    institucion_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("instituciones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    docente_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    programa: Mapped[str] = mapped_column(String(120), nullable=False)
    trimestre: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[EstadoFicha] = mapped_column(
        Enum(EstadoFicha, name="estado_ficha"), default=EstadoFicha.ACTIVA, nullable=False
    )

    docente: Mapped[Usuario] = relationship(
        back_populates="fichas_impartidas", foreign_keys=[docente_id]
    )
    inscripciones: Mapped[list["Inscripcion"]] = relationship(
        back_populates="ficha", cascade="all, delete-orphan"
    )
    guias: Mapped[list["Guia"]] = relationship(back_populates="ficha", cascade="all, delete-orphan")


class Inscripcion(ModeloBase):
    """Une un aprendiz con una ficha."""

    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint("ficha_id", "aprendiz_id", name="uq_inscripcion_ficha_aprendiz"),
        Index("idx_inscripcion_aprendiz", "aprendiz_id", "estado"),
    )

    ficha_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False
    )
    aprendiz_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[EstadoInscripcion] = mapped_column(
        Enum(EstadoInscripcion, name="estado_inscripcion"),
        default=EstadoInscripcion.ACTIVA,
        nullable=False,
    )

    ficha: Mapped[Ficha] = relationship(back_populates="inscripciones")
    aprendiz: Mapped[Usuario] = relationship(back_populates="inscripciones")


class Guia(ModeloBase):
    """Guía de aprendizaje. Sustituye a los ficheros `proyectos/*.md` de la v1."""

    __tablename__ = "guias"
    __table_args__ = (
        CheckConstraint("cierra_en > abre_en", name="ck_guia_ventana_valida"),
        CheckConstraint("num_preguntas BETWEEN 3 AND 20", name="ck_guia_num_preguntas"),
        Index("idx_guia_ficha_estado", "ficha_id", "estado"),
    )

    ficha_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("fichas.id", ondelete="CASCADE"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    # Markdown. Es lo que se inyecta en el prompt del agente y ancla las
    # preguntas al temario real de la guía.
    contexto_tecnico: Mapped[str | None] = mapped_column(Text)
    num_preguntas: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    estado: Mapped[EstadoGuia] = mapped_column(
        Enum(EstadoGuia, name="estado_guia"), default=EstadoGuia.BORRADOR, nullable=False
    )
    abre_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cierra_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ficha: Mapped[Ficha] = relationship(back_populates="guias")
    rubrica: Mapped["Rubrica | None"] = relationship(
        back_populates="guia", cascade="all, delete-orphan", uselist=False
    )
    sesiones: Mapped[list["Sesion"]] = relationship(back_populates="guia")


class Rubrica(ModeloBase):
    """Criterios de evaluación de una guía (relación 1:1).

    Sustituye al diccionario `SCORING_CRITERIA` hardcodeado de la v1 (deuda D8).
    La suma de los pesos de sus criterios debe ser 100; se valida en la capa de
    servicio para poder devolver un 422 con un mensaje útil.
    """

    __tablename__ = "rubricas"

    guia_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("guias.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    umbral_aprobacion: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    guia: Mapped[Guia] = relationship(back_populates="rubrica")
    criterios: Mapped[list["CriterioRubrica"]] = relationship(
        back_populates="rubrica",
        cascade="all, delete-orphan",
        order_by="CriterioRubrica.orden",
    )

    def a_dict(self) -> dict:
        """Serializa la rúbrica para congelarla en la sesión (ADR-007)."""
        return {
            "version_esquema": 1,
            "umbral_aprobacion": self.umbral_aprobacion,
            "criterios": [
                {"nombre": c.nombre, "descripcion": c.descripcion, "peso": c.peso}
                for c in self.criterios
            ],
        }


class CriterioRubrica(ModeloBase):
    __tablename__ = "criterios_rubrica"
    __table_args__ = (CheckConstraint("peso BETWEEN 1 AND 100", name="ck_criterio_peso"),)

    rubrica_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("rubricas.id", ondelete="CASCADE"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    peso: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rubrica: Mapped[Rubrica] = relationship(back_populates="criterios")
