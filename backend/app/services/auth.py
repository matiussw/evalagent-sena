"""Servicio de autenticación (T-002, T-003)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    ErrorToken,
    crear_token_acceso,
    crear_token_refresco,
    decodificar_token,
    hashear_password,
    verificar_password,
)
from app.models.enums import RolUsuario
from app.models.identidad import Institucion, Usuario
from app.schemas.identidad import RegistroRequest, TokenResponse, UsuarioPublico
from app.services.errores import (
    Conflicto,
    CredencialesInvalidas,
    DemasiadosIntentos,
    ReglaDeNegocio,
)

_settings = get_settings()


class LimitadorIntentos:
    """Ventana deslizante en memoria contra la fuerza bruta en el login.

    Suficiente para una instancia única, que es el modelo de despliegue previsto
    (una instancia por centro de formación). Con varias réplicas habría que
    moverlo a Redis.
    """

    def __init__(self, maximo: int, ventana_segundos: int) -> None:
        self._maximo = maximo
        self._ventana = ventana_segundos
        self._intentos: dict[str, deque[float]] = defaultdict(deque)

    def registrar_fallo(self, clave: str) -> None:
        self._intentos[clave].append(time.monotonic())

    def bloqueado(self, clave: str) -> bool:
        ahora = time.monotonic()
        cola = self._intentos[clave]
        while cola and ahora - cola[0] > self._ventana:
            cola.popleft()
        return len(cola) >= self._maximo

    def limpiar(self, clave: str) -> None:
        self._intentos.pop(clave, None)


limitador = LimitadorIntentos(_settings.LOGIN_INTENTOS_MAX, _settings.LOGIN_VENTANA_SEGUNDOS)


class ServicioAuth:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def _por_email(self, email: str) -> Usuario | None:
        resultado = await self._sesion.execute(
            select(Usuario).where(Usuario.email == email.lower())
        )
        return resultado.scalar_one_or_none()

    async def registrar_docente(self, datos: RegistroRequest) -> TokenResponse:
        if await self._por_email(datos.email):
            raise Conflicto("El correo ya está registrado")

        institucion = await self._sesion.get(Institucion, datos.institucion_id)
        if institucion is None or not institucion.activa:
            raise ReglaDeNegocio("La institución indicada no existe o está inactiva")

        usuario = Usuario(
            nombre=datos.nombre,
            email=datos.email.lower(),
            password_hash=hashear_password(datos.password),
            # El rol lo asigna el servidor. Aunque el cliente enviara
            # {"rol": "ADMIN"}, el esquema de entrada no tiene ese campo.
            rol=RolUsuario.DOCENTE,
            institucion_id=institucion.id,
        )
        self._sesion.add(usuario)
        await self._sesion.flush()
        return self._emitir_tokens(usuario)

    async def login(self, email: str, password: str) -> TokenResponse:
        clave = email.lower()

        if limitador.bloqueado(clave):
            raise DemasiadosIntentos(
                "Demasiados intentos fallidos. Espera un minuto e inténtalo de nuevo."
            )

        usuario = await self._por_email(clave)

        # Se verifica siempre contra un hash, exista o no el usuario: si solo se
        # verificara cuando existe, el tiempo de respuesta revelaría qué correos
        # están registrados.
        hash_referencia = usuario.password_hash if usuario else _HASH_SEÑUELO
        valido = verificar_password(password, hash_referencia)

        if not usuario or not valido or not usuario.activo:
            limitador.registrar_fallo(clave)
            # Mensaje genérico a propósito: no revela si el correo existe.
            raise CredencialesInvalidas("Credenciales inválidas")

        limitador.limpiar(clave)
        return self._emitir_tokens(usuario)

    async def refrescar(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decodificar_token(refresh_token, tipo_esperado="refresh")
        except ErrorToken as exc:
            raise CredencialesInvalidas(str(exc)) from exc

        usuario = await self._sesion.get(Usuario, uuid.UUID(payload["sub"]))
        if usuario is None or not usuario.activo:
            raise CredencialesInvalidas("La cuenta ya no está activa")
        return self._emitir_tokens(usuario)

    @staticmethod
    def _emitir_tokens(usuario: Usuario) -> TokenResponse:
        return TokenResponse(
            access_token=crear_token_acceso(
                usuario_id=usuario.id,
                rol=usuario.rol.value,
                institucion_id=usuario.institucion_id,
            ),
            refresh_token=crear_token_refresco(usuario_id=usuario.id),
            usuario=UsuarioPublico.model_validate(usuario),
        )


# Hash fijo contra el que comparar cuando el usuario no existe, para que el
# login tarde lo mismo en ambos casos.
_HASH_SEÑUELO = hashear_password("señuelo-para-igualar-tiempos")
