"""Hash de contraseñas y emisión/validación de JWT (T-003).

El *claim* `tid` (institución) viaja dentro del token porque es la pieza sobre la
que se apoya todo el aislamiento multi-tenant: el tenant se deriva siempre del
token, nunca de un parámetro que envíe el cliente.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

TipoToken = Literal["access", "refresh", "ws_ticket"]

_settings = get_settings()
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=_settings.BCRYPT_ROUNDS)


class ErrorToken(Exception):
    """El token es inválido, ha caducado o no es del tipo esperado."""


# --------------------------------------------------------------------------- #
# Contraseñas
# --------------------------------------------------------------------------- #


def hashear_password(password: str) -> str:
    return _pwd.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #


def _crear_token(*, sub: str, tipo: TipoToken, expira_en: timedelta, extra: dict[str, Any]) -> str:
    ahora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": sub,
        "type": tipo,
        "iat": ahora,
        "exp": ahora + expira_en,
        **extra,
    }
    return jwt.encode(payload, _settings.SECRET_KEY, algorithm=_settings.ALGORITMO_JWT)


def crear_token_acceso(*, usuario_id: UUID, rol: str, institucion_id: UUID) -> str:
    return _crear_token(
        sub=str(usuario_id),
        tipo="access",
        expira_en=timedelta(minutes=_settings.MINUTOS_TOKEN_ACCESO),
        extra={"rol": rol, "tid": str(institucion_id)},
    )


def crear_token_refresco(*, usuario_id: UUID) -> str:
    return _crear_token(
        sub=str(usuario_id),
        tipo="refresh",
        expira_en=timedelta(days=_settings.DIAS_TOKEN_REFRESCO),
        extra={},
    )


def crear_ticket_ws(*, sesion_id: UUID, aprendiz_id: UUID, jti: str) -> str:
    """Ticket de un solo uso para abrir el canal de voz (T-008).

    En la v1 bastaba con adivinar un `session_id` para conectarse al WebSocket.
    El ticket está ligado a la sesión y al aprendiz, caduca en 60 s y `jti`
    permite invalidarlo tras el primer uso.
    """
    return _crear_token(
        sub=str(aprendiz_id),
        tipo="ws_ticket",
        expira_en=timedelta(seconds=_settings.SEGUNDOS_TICKET_WS),
        extra={"sid": str(sesion_id), "jti": jti},
    )


def decodificar_token(token: str, *, tipo_esperado: TipoToken) -> dict[str, Any]:
    """Decodifica y valida un token.

    Comprobar `tipo_esperado` evita que un token de refresco sirva para
    autenticar peticiones normales, o que un ticket de WebSocket valga como
    token de acceso.
    """
    try:
        payload = jwt.decode(token, _settings.SECRET_KEY, algorithms=[_settings.ALGORITMO_JWT])
    except JWTError as exc:
        raise ErrorToken("Token inválido o caducado") from exc

    if payload.get("type") != tipo_esperado:
        raise ErrorToken(
            f"Se esperaba un token de tipo '{tipo_esperado}' y se recibió '{payload.get('type')}'"
        )
    return payload
