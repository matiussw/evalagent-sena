"""Tests de integración de autenticación (T-002, T-003)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_registro_exitoso(cliente, institucion_a):
    r = await cliente.post(
        "/auth/registro",
        json={
            "nombre": "Carolina Restrepo",
            "email": "nueva.docente@sena.edu.co",
            "password": "unaClaveSegura2026",
            "institucion_id": str(institucion_a.id),
        },
    )

    assert r.status_code == 201
    datos = r.json()
    assert datos["usuario"]["rol"] == "DOCENTE"
    assert datos["access_token"] and datos["refresh_token"]
    # El hash nunca sale en la respuesta.
    assert "password" not in r.text.lower() or "password_hash" not in r.text


async def test_registro_con_correo_duplicado(cliente, institucion_a, docente_a):
    r = await cliente.post(
        "/auth/registro",
        json={
            "nombre": "Impostora",
            "email": docente_a.email,
            "password": "otraClaveSegura2026",
            "institucion_id": str(institucion_a.id),
        },
    )

    assert r.status_code == 409
    assert "ya está registrado" in r.json()["detail"]


async def test_registro_con_password_corta(cliente, institucion_a):
    r = await cliente.post(
        "/auth/registro",
        json={
            "nombre": "Carolina",
            "email": "corta@sena.edu.co",
            "password": "1234",
            "institucion_id": str(institucion_a.id),
        },
    )
    assert r.status_code == 422


async def test_no_se_puede_escalar_a_admin_desde_el_registro(cliente, institucion_a):
    """El rol lo asigna el servidor: el esquema de entrada no tiene ese campo."""
    r = await cliente.post(
        "/auth/registro",
        json={
            "nombre": "Aspirante",
            "email": "aspirante@sena.edu.co",
            "password": "unaClaveSegura2026",
            "institucion_id": str(institucion_a.id),
            "rol": "ADMIN",
        },
    )

    assert r.status_code == 201
    assert r.json()["usuario"]["rol"] == "DOCENTE"


async def test_login_correcto(cliente, docente_a):
    r = await cliente.post(
        "/auth/login",
        data={"username": docente_a.email, "password": "claveDePrueba2026"},
    )

    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == docente_a.email


async def test_login_con_password_incorrecta(cliente, docente_a):
    r = await cliente.post(
        "/auth/login", data={"username": docente_a.email, "password": "equivocada"}
    )

    assert r.status_code == 401
    # Mensaje genérico: no revela si el correo existe.
    assert r.json()["detail"] == "Credenciales inválidas"


async def test_login_con_correo_inexistente_da_el_mismo_mensaje(cliente, institucion_a):
    r = await cliente.post(
        "/auth/login", data={"username": "nadie@sena.edu.co", "password": "loquesea"}
    )

    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciales inválidas"


async def test_yo_devuelve_el_usuario_autenticado(cliente, docente_a, token_de):
    r = await cliente.get("/auth/yo", headers=token_de(docente_a))

    assert r.status_code == 200
    assert r.json()["email"] == docente_a.email
    assert "password_hash" not in r.json()


async def test_endpoint_protegido_sin_token(cliente):
    r = await cliente.get("/auth/yo")
    assert r.status_code == 401


async def test_refresh_emite_tokens_nuevos(cliente, docente_a):
    login = await cliente.post(
        "/auth/login",
        data={"username": docente_a.email, "password": "claveDePrueba2026"},
    )
    refresco = login.json()["refresh_token"]

    r = await cliente.post("/auth/refresh", json={"refresh_token": refresco})

    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_un_refresh_no_autentica_peticiones(cliente, docente_a):
    login = await cliente.post(
        "/auth/login",
        data={"username": docente_a.email, "password": "claveDePrueba2026"},
    )
    refresco = login.json()["refresh_token"]

    r = await cliente.get("/auth/yo", headers={"Authorization": f"Bearer {refresco}"})

    assert r.status_code == 401


async def test_bloqueo_por_fuerza_bruta(cliente, docente_a):
    """Criterio de aceptación T-003: al sexto intento fallido se devuelve 429."""
    from app.services.auth import limitador

    limitador.limpiar(docente_a.email)

    for _ in range(5):
        await cliente.post("/auth/login", data={"username": docente_a.email, "password": "mal"})

    r = await cliente.post("/auth/login", data={"username": docente_a.email, "password": "mal"})

    assert r.status_code == 429
    limitador.limpiar(docente_a.email)
