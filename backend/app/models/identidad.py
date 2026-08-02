"""Institución (tenant raíz) y Usuario (T-001)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ModeloBase
from app.models.enums import RolUsuario

if TYPE_CHECKING:
    from app.models.academico import Ficha, Inscripcion


class Institucion(ModeloBase):
    """Tenant raíz. Todo dato del sistema cuelga de una institución."""

    __tablename__ = "instituciones"

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="institucion")

    def __repr__(self) -> str:
        return f"<Institucion {self.nit} {self.nombre!r}>"


class Usuario(ModeloBase):
    __tablename__ = "usuarios"
    __table_args__ = (
        # Soporta el listado de aprendices de un centro, la consulta más
        # frecuente del panel docente.
        Index("idx_usuario_institucion_rol", "institucion_id", "rol"),
    )

    institucion_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("instituciones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    # Único global, no por tenant: una persona, una cuenta.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, name="rol_usuario"), nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    institucion: Mapped[Institucion] = relationship(back_populates="usuarios")
    fichas_impartidas: Mapped[list["Ficha"]] = relationship(
        back_populates="docente", foreign_keys="Ficha.docente_id"
    )
    inscripciones: Mapped[list["Inscripcion"]] = relationship(
        back_populates="aprendiz"
    )

    def __repr__(self) -> str:
        # El hash de la contraseña nunca aparece en la representación.
        return f"<Usuario {self.email} rol={self.rol}>"
