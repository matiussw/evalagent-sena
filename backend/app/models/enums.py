"""Enumerados del dominio."""

from enum import StrEnum


class RolUsuario(StrEnum):
    ADMIN = "ADMIN"
    DOCENTE = "DOCENTE"
    APRENDIZ = "APRENDIZ"


class EstadoFicha(StrEnum):
    ACTIVA = "ACTIVA"
    ARCHIVADA = "ARCHIVADA"


class EstadoInscripcion(StrEnum):
    ACTIVA = "ACTIVA"
    RETIRADA = "RETIRADA"


class EstadoGuia(StrEnum):
    BORRADOR = "BORRADOR"
    PUBLICADA = "PUBLICADA"
    CERRADA = "CERRADA"


class EstadoSesion(StrEnum):
    """Máquina de estados de la sustentación.

    La transición a CALIFICADA exige una fila en `revisiones` (regla RI-4).
    Ver ADR-006: ninguna nota se publica sin confirmación humana.
    """

    INICIADA = "INICIADA"
    EN_CURSO = "EN_CURSO"
    PENDIENTE_REVISION = "PENDIENTE_REVISION"
    CALIFICADA = "CALIFICADA"
    EN_RECLAMACION = "EN_RECLAMACION"
    ABANDONADA = "ABANDONADA"


class RolTurno(StrEnum):
    AGENTE = "AGENTE"
    APRENDIZ = "APRENDIZ"


class AccionAuditoria(StrEnum):
    SESION_INICIADA = "SESION_INICIADA"
    SESION_FINALIZADA = "SESION_FINALIZADA"
    SESION_ABANDONADA = "SESION_ABANDONADA"
    NOTA_CONFIRMADA = "NOTA_CONFIRMADA"
    RECLAMACION_ABIERTA = "RECLAMACION_ABIERTA"
    ACCESO_CRUZADO_BLOQUEADO = "ACCESO_CRUZADO_BLOQUEADO"
