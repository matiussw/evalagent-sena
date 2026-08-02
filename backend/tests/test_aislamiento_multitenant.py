"""Aislamiento entre instituciones (HU-03 · T-004 · ADR-003).

Este es el test más importante de la suite: una fuga entre instituciones es un
incidente de protección de datos personales, no un bug menor.

Está **parametrizado sobre todos los endpoints de dominio**, no sobre una
muestra. El riesgo real no está en los endpoints que existen hoy, sino en el que
se escriba dentro de tres semanas — por eso `test_ningun_endpoint_queda_sin_cubrir`
falla si alguien añade una ruta y olvida incluirla aquí.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

# Endpoints de dominio con el recurso de otra institución en la ruta.
# Formato: (rol del intruso, método, plantilla de ruta, cuerpo)
#
# El rol importa: cada endpoint se prueba con el rol que *sí* tiene permiso para
# invocarlo, de modo que lo único que puede rechazar la petición sea el filtro de
# tenant. Probar un endpoint de aprendiz con un docente daría un 403 por rol y
# enmascararía una posible fuga.
ENDPOINTS_CON_RECURSO = [
    ("docente", "GET", "/fichas/{ficha_id}", None),
    ("docente", "PATCH", "/fichas/{ficha_id}", {"nombre": "Secuestrada"}),
    ("docente", "POST", "/fichas/{ficha_id}/archivar", None),
    ("docente", "GET", "/fichas/{ficha_id}/guias", None),
    ("docente", "POST", "/fichas/{ficha_id}/guias", {"titulo": "Intrusa"}),
    ("docente", "GET", "/fichas/{ficha_id}/inscripciones", None),
    ("docente", "POST", "/fichas/{ficha_id}/inscripciones", {"email": "intruso@sena.edu.co"}),
    ("docente", "GET", "/guias/{guia_id}", None),
    ("docente", "PATCH", "/guias/{guia_id}", {"titulo": "Secuestrada"}),
    ("docente", "POST", "/guias/{guia_id}/publicar", None),
    ("docente", "GET", "/guias/{guia_id}/rubrica", None),
    ("docente", "GET", "/sesiones/{sesion_id}/revision", None),
    ("aprendiz", "GET", "/sesiones/{sesion_id}", None),
    ("aprendiz", "POST", "/sesiones/{sesion_id}/latido", None),
    ("aprendiz", "POST", "/sesiones/{sesion_id}/reclamar", None),
]

# Endpoints sin recurso en la ruta: se verifica que el listado sale filtrado.
ENDPOINTS_DE_LISTADO = [
    "/fichas",
    "/sesiones",
]


@pytest.fixture
async def recursos_de_a(bd, institucion_a, docente_a, aprendiz_a, ficha_a, rubrica_valida):
    """Ficha, guía y sesión pertenecientes a la institución A."""
    from datetime import UTC, datetime, timedelta

    from app.models import (
        CriterioRubrica,
        EstadoGuia,
        Guia,
        Inscripcion,
        Rubrica,
        Sesion,
    )

    ahora = datetime.now(UTC)
    guia = Guia(
        ficha_id=ficha_a.id,
        titulo="API REST de gestión de tareas",
        contexto_tecnico="Endpoints, códigos HTTP y manejo de errores.",
        num_preguntas=8,
        estado=EstadoGuia.PUBLICADA,
        abre_en=ahora - timedelta(days=1),
        cierra_en=ahora + timedelta(days=10),
    )
    bd.add(guia)
    await bd.flush()

    rubrica = Rubrica(guia_id=guia.id, umbral_aprobacion=60)
    rubrica.criterios = [
        CriterioRubrica(nombre=c["nombre"], descripcion=c["descripcion"], peso=c["peso"], orden=i)
        for i, c in enumerate(rubrica_valida["criterios"])
    ]
    bd.add(rubrica)
    bd.add(Inscripcion(ficha_id=ficha_a.id, aprendiz_id=aprendiz_a.id))
    await bd.flush()

    sesion = Sesion(
        guia_id=guia.id,
        aprendiz_id=aprendiz_a.id,
        rubrica_congelada=rubrica.a_dict(),
        consentimiento_aceptado_en=ahora,
        iniciada_en=ahora,
        ultimo_latido=ahora,
    )
    bd.add(sesion)
    await bd.commit()

    return {"ficha_id": ficha_a.id, "guia_id": guia.id, "sesion_id": sesion.id}


@pytest.mark.parametrize(("rol", "metodo", "plantilla", "cuerpo"), ENDPOINTS_CON_RECURSO)
async def test_no_se_accede_a_recursos_de_otra_institucion(
    cliente, token_de, docente_b, aprendiz_b, recursos_de_a, rol, metodo, plantilla, cuerpo
):
    """Un usuario de la institución B recibe 404 en cualquier recurso de A.

    Se exige 404 y no 403: un 403 confirmaría que el recurso existe.
    """
    intruso = docente_b if rol == "docente" else aprendiz_b
    ruta = plantilla.format(**{k: str(v) for k, v in recursos_de_a.items()})

    respuesta = await cliente.request(
        metodo, ruta, headers=token_de(intruso), json=cuerpo
    )

    assert respuesta.status_code == 404, (
        f"{metodo} {ruta} como {rol} devolvió {respuesta.status_code} en lugar "
        f"de 404. Cuerpo: {respuesta.text[:200]}"
    )


@pytest.mark.parametrize("ruta", ENDPOINTS_DE_LISTADO)
async def test_los_listados_solo_devuelven_datos_del_propio_tenant(
    cliente, token_de, docente_b, recursos_de_a, ruta
):
    respuesta = await cliente.get(ruta, headers=token_de(docente_b))

    assert respuesta.status_code == 200
    assert respuesta.json() == [], (
        f"{ruta} filtró datos de otra institución: {respuesta.text[:200]}"
    )


async def test_el_tenant_no_se_puede_falsear_desde_el_cuerpo(
    cliente, token_de, docente_a, institucion_b
):
    """El tenant se toma del token, nunca del cuerpo de la petición."""
    respuesta = await cliente.post(
        "/fichas",
        headers=token_de(docente_a),
        json={
            "codigo": "9999999",
            "nombre": "Intento de fuga",
            "programa": "ADSO",
            "trimestre": "2026-2",
            "institucion_id": str(institucion_b.id),
        },
    )

    assert respuesta.status_code == 201

    # La ficha existe para su docente (institución A)...
    ficha_id = respuesta.json()["id"]
    propia = await cliente.get(f"/fichas/{ficha_id}", headers=token_de(docente_a))
    assert propia.status_code == 200


async def test_el_mismo_codigo_de_ficha_puede_repetirse_entre_instituciones(
    cliente, token_de, docente_a, docente_b, ficha_a
):
    respuesta = await cliente.post(
        "/fichas",
        headers=token_de(docente_b),
        json={
            "codigo": ficha_a.codigo,
            "nombre": "Misma numeración, otro centro",
            "programa": "ADSO",
            "trimestre": "2026-2",
        },
    )

    assert respuesta.status_code == 201


async def test_codigo_duplicado_dentro_de_la_misma_institucion_es_conflicto(
    cliente, token_de, docente_a, ficha_a
):
    respuesta = await cliente.post(
        "/fichas",
        headers=token_de(docente_a),
        json={
            "codigo": ficha_a.codigo,
            "nombre": "Duplicada",
            "programa": "ADSO",
            "trimestre": "2026-2",
        },
    )

    assert respuesta.status_code == 409


async def test_ningun_endpoint_queda_sin_cubrir():
    """Guardia contra el olvido.

    Si alguien añade un endpoint de dominio y no lo incluye en las listas de
    arriba, este test falla. Sin él, la cobertura del aislamiento envejecería
    en silencio.
    """
    from app.main import app

    cubiertos = {p for _, _, p, _ in ENDPOINTS_CON_RECURSO} | set(ENDPOINTS_DE_LISTADO)

    # Rutas exentas: no reciben el identificador de un recurso de dominio, así
    # que no hay recurso ajeno al que fugarse.
    exentas = {
        "/api/v1/health",
        "/api/v1/auth/registro",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/yo",
        # Filtran por el propio usuario autenticado.
        "/api/v1/mis-guias",
        "/api/v1/mis-resultados",
    }

    del_esquema = {
        ruta.removeprefix("/api/v1")
        for ruta in app.openapi()["paths"]
        if ruta not in exentas
    }
    sin_cubrir = del_esquema - cubiertos

    assert not sin_cubrir, (
        "Estos endpoints de dominio no están cubiertos por el test de "
        f"aislamiento multi-tenant: {sorted(sin_cubrir)}. "
        "Añádelos a ENDPOINTS_CON_RECURSO o a ENDPOINTS_DE_LISTADO."
    )
