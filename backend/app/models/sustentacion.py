"""Sesión de sustentación, turnos, revisión y auditoría (T-007, T-011)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ModeloBase
from app.models.enums import AccionAuditoria, EstadoSesion, RolTurno

if TYPE_CHECKING:
    from app.models.academico import Guia
    from app.models.identidad import Usuario


class Sesion(ModeloBase):
    """Una sustentación.

    El estado deja de vivir en un `dict` en memoria (deuda D7 de la v1) y pasa a
    la base de datos, lo que habilita la reanudación y la auditoría.

    No existe ninguna columna de audio: solo se persiste la transcripción
    textual (RNF-09).
    """

    __tablename__ = "sesiones"
    __table_args__ = (
        Index("idx_sesion_guia_estado", "guia_id", "estado"),
        Index("idx_sesion_aprendiz", "aprendiz_id"),
        # RI-7: un aprendiz tiene como máximo una sesión no abandonada por guía.
        Index(
            "idx_sesion_unica_por_guia",
            "guia_id",
            "aprendiz_id",
            unique=True,
            postgresql_where=text("estado <> 'ABANDONADA'"),
        ),
    )

    guia_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("guias.id", ondelete="RESTRICT"), nullable=False
    )
    aprendiz_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[EstadoSesion] = mapped_column(
        Enum(EstadoSesion, name="estado_sesion"),
        default=EstadoSesion.INICIADA,
        nullable=False,
    )

    # Copia inmutable de la rúbrica en el momento de sustentar (ADR-007).
    # Si el instructor la edita después, las notas ya emitidas siguen cuadrando.
    rubrica_congelada: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Propuesta del agente. Se conserva aunque el instructor la modifique:
    # es la evidencia de auditoría y alimenta los KPIs K4 y K5.
    puntuaciones_agente: Mapped[dict | None] = mapped_column(JSONB)

    modelo_llm: Mapped[str | None] = mapped_column(String(80))
    version_prompt: Mapped[str | None] = mapped_column(String(20))
    preguntas_respondidas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    consentimiento_aceptado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    iniciada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_latido: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    guia: Mapped["Guia"] = relationship(back_populates="sesiones")
    aprendiz: Mapped["Usuario"] = relationship()
    turnos: Mapped[list["TurnoConversacion"]] = relationship(
        back_populates="sesion",
        cascade="all, delete-orphan",
        order_by="TurnoConversacion.orden",
    )
    revision: Mapped["Revision | None"] = relationship(back_populates="sesion", uselist=False)


class TurnoConversacion(ModeloBase):
    """Una intervención de la conversación. Solo texto, nunca audio."""

    __tablename__ = "turnos_conversacion"
    __table_args__ = (
        UniqueConstraint("sesion_id", "orden", name="uq_turno_sesion_orden"),
        Index("idx_turno_sesion_orden", "sesion_id", "orden"),
    )

    sesion_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sesiones.id", ondelete="CASCADE"), nullable=False
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    rol: Mapped[RolTurno] = mapped_column(Enum(RolTurno, name="rol_turno"), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    # Alimenta el KPI de latencia de turno (RNF-01).
    latencia_ms: Mapped[int | None] = mapped_column(Integer)

    sesion: Mapped[Sesion] = relationship(back_populates="turnos")


class Revision(ModeloBase):
    """Confirmación humana de la calificación (ADR-006).

    La existencia de una fila aquí es lo que distingue una nota publicada de una
    simple propuesta del agente. Sin ella, la sesión no puede llegar a
    CALIFICADA (regla RI-4).
    """

    __tablename__ = "revisiones"

    sesion_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("sesiones.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    revisor_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    puntuaciones_finales: Mapped[dict] = mapped_column(JSONB, nullable=False)
    retroalimentacion: Mapped[str | None] = mapped_column(Text)
    nota_final: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confirmada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sesion: Mapped[Sesion] = relationship(back_populates="revision")
    revisor: Mapped["Usuario"] = relationship()


class EventoAuditoria(ModeloBase):
    """Rastro inmutable. Append-only: sin UPDATE ni DELETE (regla RI-8)."""

    __tablename__ = "eventos_auditoria"
    __table_args__ = (Index("idx_auditoria_sesion_fecha", "sesion_id", "creado_en"),)

    sesion_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sesiones.id", ondelete="SET NULL")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    accion: Mapped[AccionAuditoria] = mapped_column(
        Enum(AccionAuditoria, name="accion_auditoria"), nullable=False
    )
    detalle: Mapped[dict | None] = mapped_column(JSONB)
