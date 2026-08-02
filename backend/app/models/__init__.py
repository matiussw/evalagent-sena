"""Modelos del dominio.

Se reexportan todos para que Alembic los descubra al autogenerar migraciones.
"""

from app.db.base import Base, ModeloBase
from app.models.academico import CriterioRubrica, Ficha, Guia, Inscripcion, Rubrica
from app.models.enums import (
    AccionAuditoria,
    EstadoFicha,
    EstadoGuia,
    EstadoInscripcion,
    EstadoSesion,
    RolTurno,
    RolUsuario,
)
from app.models.identidad import Institucion, Usuario
from app.models.sustentacion import (
    EventoAuditoria,
    Revision,
    Sesion,
    TurnoConversacion,
)

__all__ = [
    "AccionAuditoria",
    "Base",
    "CriterioRubrica",
    "EstadoFicha",
    "EstadoGuia",
    "EstadoInscripcion",
    "EstadoSesion",
    "EventoAuditoria",
    "Ficha",
    "Guia",
    "Inscripcion",
    "Institucion",
    "ModeloBase",
    "Revision",
    "RolTurno",
    "RolUsuario",
    "Rubrica",
    "Sesion",
    "TurnoConversacion",
    "Usuario",
]
