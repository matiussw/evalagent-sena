"""Flujo E2E del dominio académico (HU-05, HU-06, HU-07, HU-11).

Recorre el camino completo del instructor: crear ficha → publicar guía con
rúbrica → inscribir aprendiz → el aprendiz ve la guía y puede sustentarla.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.asyncio


def _ventana(dias_antes: int = 1, dias_despues: int = 10) -> dict[str, str]:
    ahora = datetime.now(UTC)
    return {
        "abre_en": (ahora - timedelta(days=dias_antes)).isoformat(),
        "cierra_en": (ahora + timedelta(days=dias_despues)).isoformat(),
    }


async def test_flujo_completo_del_instructor(
    cliente, token_de, docente_a, aprendiz_a, rubrica_valida
):
    cabeceras = token_de(docente_a)

    # 1. Crear la ficha
    ficha = await cliente.post(
        "/fichas",
        headers=cabeceras,
        json={
            "codigo": "2758421",
            "nombre": "Análisis y Desarrollo de Software",
            "programa": "ADSO",
            "trimestre": "2026-2",
        },
    )
    assert ficha.status_code == 201
    ficha_id = ficha.json()["id"]

    # 2. Crear la guía (nace en BORRADOR)
    guia = await cliente.post(
        f"/fichas/{ficha_id}/guias",
        headers=cabeceras,
        json={
            "titulo": "API REST de gestión de tareas",
            "descripcion": "Sustentación de la competencia 220501096",
            "contexto_tecnico": "## Temas\n- Endpoints y verbos HTTP\n- Códigos de estado",
            "num_preguntas": 8,
            **_ventana(),
        },
    )
    assert guia.status_code == 201
    assert guia.json()["estado"] == "BORRADOR"
    guia_id = guia.json()["id"]

    # 3. Definir la rúbrica
    rubrica = await cliente.put(
        f"/guias/{guia_id}/rubrica", headers=cabeceras, json=rubrica_valida
    )
    assert rubrica.status_code == 200
    assert len(rubrica.json()["criterios"]) == 5

    # 4. Publicar
    publicada = await cliente.post(f"/guias/{guia_id}/publicar", headers=cabeceras)
    assert publicada.status_code == 200
    assert publicada.json()["estado"] == "PUBLICADA"

    # 5. Inscribir al aprendiz
    inscripcion = await cliente.post(
        f"/fichas/{ficha_id}/inscripciones",
        headers=cabeceras,
        json={"email": aprendiz_a.email},
    )
    assert inscripcion.status_code == 201

    # 6. El aprendiz ya ve la guía
    mis_guias = await cliente.get("/mis-guias", headers=token_de(aprendiz_a))
    assert mis_guias.status_code == 200
    assert [g["id"] for g in mis_guias.json()] == [guia_id]


async def test_una_guia_en_borrador_no_la_ve_el_aprendiz(
    cliente, token_de, docente_a, aprendiz_a, ficha_a
):
    await cliente.post(
        f"/fichas/{ficha_a.id}/inscripciones",
        headers=token_de(docente_a),
        json={"email": aprendiz_a.email},
    )
    await cliente.post(
        f"/fichas/{ficha_a.id}/guias",
        headers=token_de(docente_a),
        json={"titulo": "Guía sin publicar", "contexto_tecnico": "algo", **_ventana()},
    )

    r = await cliente.get("/mis-guias", headers=token_de(aprendiz_a))

    assert r.json() == []


async def test_no_se_publica_sin_contexto_tecnico(
    cliente, token_de, docente_a, ficha_a, rubrica_valida
):
    """Sin contexto, el agente preguntaría de cualquier cosa."""
    guia = await cliente.post(
        f"/fichas/{ficha_a.id}/guias",
        headers=token_de(docente_a),
        json={"titulo": "Sin contexto", **_ventana()},
    )
    guia_id = guia.json()["id"]
    await cliente.put(
        f"/guias/{guia_id}/rubrica", headers=token_de(docente_a), json=rubrica_valida
    )

    r = await cliente.post(f"/guias/{guia_id}/publicar", headers=token_de(docente_a))

    assert r.status_code == 422
    assert "contexto técnico" in r.json()["detail"]


async def test_no_se_publica_sin_rubrica(cliente, token_de, docente_a, ficha_a):
    """Sin rúbrica no habría criterio con el que calificar."""
    guia = await cliente.post(
        f"/fichas/{ficha_a.id}/guias",
        headers=token_de(docente_a),
        json={"titulo": "Sin rúbrica", "contexto_tecnico": "Endpoints", **_ventana()},
    )

    r = await cliente.post(
        f"/guias/{guia.json()['id']}/publicar", headers=token_de(docente_a)
    )

    assert r.status_code == 422
    assert "rúbrica" in r.json()["detail"]


@pytest.mark.parametrize("pesos", [[25, 20, 20, 15, 10], [30, 30, 20, 15, 20]])
async def test_los_pesos_de_la_rubrica_deben_sumar_cien(
    cliente, token_de, docente_a, ficha_a, rubrica_valida, pesos
):
    guia = await cliente.post(
        f"/fichas/{ficha_a.id}/guias",
        headers=token_de(docente_a),
        json={"titulo": "Con rúbrica torcida", "contexto_tecnico": "x", **_ventana()},
    )
    criterios = [
        {**c, "peso": p} for c, p in zip(rubrica_valida["criterios"], pesos, strict=True)
    ]

    r = await cliente.put(
        f"/guias/{guia.json()['id']}/rubrica",
        headers=token_de(docente_a),
        json={"umbral_aprobacion": 60, "criterios": criterios},
    )

    assert r.status_code == 422


async def test_ventana_invertida_es_rechazada(cliente, token_de, docente_a, ficha_a):
    ahora = datetime.now(UTC)
    r = await cliente.post(
        f"/fichas/{ficha_a.id}/guias",
        headers=token_de(docente_a),
        json={
            "titulo": "Ventana imposible",
            "abre_en": (ahora + timedelta(days=5)).isoformat(),
            "cierra_en": ahora.isoformat(),
        },
    )
    assert r.status_code == 422


async def test_un_aprendiz_no_puede_crear_fichas(cliente, token_de, aprendiz_a):
    r = await cliente.post(
        "/fichas",
        headers=token_de(aprendiz_a),
        json={
            "codigo": "9999999",
            "nombre": "Ficha pirata",
            "programa": "ADSO",
            "trimestre": "2026-2",
        },
    )
    assert r.status_code == 403


async def test_archivar_saca_la_ficha_del_listado_activo(
    cliente, token_de, docente_a, ficha_a
):
    r = await cliente.post(f"/fichas/{ficha_a.id}/archivar", headers=token_de(docente_a))

    assert r.status_code == 200
    assert r.json()["estado"] == "ARCHIVADA"


async def test_inscribir_dos_veces_al_mismo_aprendiz_es_conflicto(
    cliente, token_de, docente_a, aprendiz_a, ficha_a
):
    cuerpo = {"email": aprendiz_a.email}
    await cliente.post(
        f"/fichas/{ficha_a.id}/inscripciones", headers=token_de(docente_a), json=cuerpo
    )

    r = await cliente.post(
        f"/fichas/{ficha_a.id}/inscripciones", headers=token_de(docente_a), json=cuerpo
    )

    assert r.status_code == 409


async def test_inscribir_un_correo_nuevo_crea_la_cuenta_del_aprendiz(
    cliente, token_de, docente_a, ficha_a
):
    r = await cliente.post(
        f"/fichas/{ficha_a.id}/inscripciones",
        headers=token_de(docente_a),
        json={"email": "nuevo.aprendiz@sena.edu.co", "nombre": "Nuevo Aprendiz"},
    )

    assert r.status_code == 201
    assert r.json()["estado"] == "ACTIVA"
