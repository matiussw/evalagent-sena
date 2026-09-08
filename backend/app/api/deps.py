"""Dependencias transversales de la API (T-003, T-004)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ErrorToken, decodificar_token
from app.db.session import get_sesion
from app.models.enums import RolUsuario
from app.models.identidad import Usuario
from app.services.errores import CredencialesInvalidas, SinPermiso

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SesionBD = Annotated[AsyncSession, Depends(get_sesion)]


async def usuario_actual(token: Annotated[str | None, Depends(oauth2)], bd: SesionBD) -> Usuario:
    if not token:
        raise CredencialesInvalidas("Falta el token de acceso")

    try:
        payload = decodificar_token(token, tipo_esperado="access")
    except ErrorToken as exc:
        raise CredencialesInvalidas(str(exc)) from exc

    usuario = await bd.get(Usuario, uuid.UUID(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise CredencialesInvalidas("La cuenta no existe o está inactiva")

    # El token podría haberse emitido antes de mover al usuario de institución.
    if str(usuario.institucion_id) != payload.get("tid"):
        raise CredencialesInvalidas("El token no corresponde a tu institución actual")

    return usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]


def requiere_rol(*roles: RolUsuario):
    """Factoría de dependencias de autorización por rol."""

    async def verificar(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in roles:
            raise SinPermiso(f"Esta acción requiere rol {' o '.join(r.value for r in roles)}")
        return usuario

    return verificar


Docente = Annotated[Usuario, Depends(requiere_rol(RolUsuario.DOCENTE))]
Aprendiz = Annotated[Usuario, Depends(requiere_rol(RolUsuario.APRENDIZ))]
Admin = Annotated[Usuario, Depends(requiere_rol(RolUsuario.ADMIN))]


async def institucion_actual(usuario: UsuarioActual) -> uuid.UUID:
    """Tenant de la petición.

    Se deriva del usuario autenticado —y por tanto del token—, nunca de un
    parámetro del cliente. Es la base del aislamiento (ADR-003).
    """
    return usuario.institucion_id


InstitucionActual = Annotated[uuid.UUID, Depends(institucion_actual)]


def ip_cliente(request: Request) -> str:
    return request.client.host if request.client else "desconocida"
