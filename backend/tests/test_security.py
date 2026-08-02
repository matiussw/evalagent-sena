"""Tests de hash de contraseñas y JWT (T-003)."""

import uuid
from datetime import timedelta

import pytest

from app.core import security


@pytest.fixture
def ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


# --------------------------------------------------------------------------- #
# Contraseñas
# --------------------------------------------------------------------------- #


def test_el_hash_no_es_reversible_ni_repetible() -> None:
    clave = "unaClaveSegura2026"
    h1 = security.hashear_password(clave)
    h2 = security.hashear_password(clave)

    assert clave not in h1
    assert h1 != h2, "cada hash debe llevar su propia sal"
    assert security.verificar_password(clave, h1)
    assert security.verificar_password(clave, h2)


def test_password_incorrecta_no_verifica() -> None:
    h = security.hashear_password("correcta")
    assert not security.verificar_password("incorrecta", h)


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #


def test_token_de_acceso_lleva_rol_y_tenant(ids) -> None:
    """El `tid` en el token es la base del aislamiento multi-tenant (ADR-003)."""
    usuario_id, institucion_id = ids
    token = security.crear_token_acceso(
        usuario_id=usuario_id, rol="DOCENTE", institucion_id=institucion_id
    )

    payload = security.decodificar_token(token, tipo_esperado="access")

    assert payload["sub"] == str(usuario_id)
    assert payload["rol"] == "DOCENTE"
    assert payload["tid"] == str(institucion_id)


def test_un_refresh_no_sirve_como_token_de_acceso(ids) -> None:
    """Criterio de aceptación T-003: los tipos de token no son intercambiables."""
    usuario_id, _ = ids
    refresh = security.crear_token_refresco(usuario_id=usuario_id)

    with pytest.raises(security.ErrorToken, match="tipo"):
        security.decodificar_token(refresh, tipo_esperado="access")


def test_un_ticket_ws_no_sirve_como_token_de_acceso(ids) -> None:
    usuario_id, _ = ids
    ticket = security.crear_ticket_ws(sesion_id=uuid.uuid4(), aprendiz_id=usuario_id, jti="abc")

    with pytest.raises(security.ErrorToken):
        security.decodificar_token(ticket, tipo_esperado="access")


def test_token_caducado_es_rechazado(ids, monkeypatch) -> None:
    usuario_id, institucion_id = ids
    caducado = security._crear_token(
        sub=str(usuario_id),
        tipo="access",
        expira_en=timedelta(seconds=-10),
        extra={"rol": "DOCENTE", "tid": str(institucion_id)},
    )

    with pytest.raises(security.ErrorToken):
        security.decodificar_token(caducado, tipo_esperado="access")


def test_token_firmado_con_otra_clave_es_rechazado(ids) -> None:
    from jose import jwt

    usuario_id, _ = ids
    falso = jwt.encode(
        {"sub": str(usuario_id), "type": "access"}, "clave-del-atacante", algorithm="HS256"
    )

    with pytest.raises(security.ErrorToken):
        security.decodificar_token(falso, tipo_esperado="access")


def test_ticket_ws_liga_sesion_y_aprendiz(ids) -> None:
    """El ticket impide conectarse al WebSocket adivinando un id de sesión."""
    aprendiz_id, _ = ids
    sesion_id = uuid.uuid4()

    ticket = security.crear_ticket_ws(sesion_id=sesion_id, aprendiz_id=aprendiz_id, jti="unico-123")
    payload = security.decodificar_token(ticket, tipo_esperado="ws_ticket")

    assert payload["sid"] == str(sesion_id)
    assert payload["sub"] == str(aprendiz_id)
    assert payload["jti"] == "unico-123"
