"""Confirmación humana obligatoria (HU-12 · T-011 · ADR-006).

Es el requisito ético y legal innegociable del sistema: el Art. 22 del RGPD y el
AI Act prohíben la decisión totalmente automatizada con efecto significativo
sobre una persona, y una nota académica lo tiene.

El último test de este módulo es el criterio de aceptación más importante de
T-011: verifica por inspección del código fuente que **no existe ninguna ruta
que lleve una sesión a CALIFICADA fuera del servicio de revisión**.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from app.models import EstadoSesion
from app.services.academico import calcular_nota


@pytest.fixture
async def sesion_pendiente(bd, institucion_a, docente_a, aprendiz_a, ficha_a, rubrica_valida):
    """Sesión terminada, con propuesta del agente, esperando revisión."""
    from datetime import UTC, datetime, timedelta

    from app.models import CriterioRubrica, EstadoGuia, Guia, Inscripcion, Rubrica, Sesion

    ahora = datetime.now(UTC)
    guia = Guia(
        ficha_id=ficha_a.id,
        titulo="API REST de gestión de tareas",
        contexto_tecnico="Endpoints, códigos HTTP y manejo de errores.",
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
        estado=EstadoSesion.PENDIENTE_REVISION,
        rubrica_congelada=rubrica.a_dict(),
        puntuaciones_agente={
            "Endpoints": 8,
            "Manejo de errores": 6,
            "Diseño": 7,
            "Seguridad": 3,
            "Explicación": 7,
        },
        consentimiento_aceptado_en=ahora,
        iniciada_en=ahora,
        finalizada_en=ahora,
    )
    bd.add(sesion)
    await bd.commit()
    return sesion


# --------------------------------------------------------------------------- #
# El aprendiz no ve nada hasta que un humano confirma
# --------------------------------------------------------------------------- #

async def test_el_aprendiz_no_ve_la_propuesta_del_agente(
    cliente, token_de, aprendiz_a, sesion_pendiente
):
    r = await cliente.get("/mis-resultados", headers=token_de(aprendiz_a))

    assert r.status_code == 200
    resultado = r.json()[0]
    assert resultado["estado"] == "PENDIENTE_REVISION"
    assert resultado["mensaje"] == "Pendiente de revisión del instructor"
    assert resultado["nota_final"] is None
    assert resultado["desglose"] is None
    # La propuesta del agente no aparece por ningún lado del cuerpo.
    assert "puntuaciones_agente" not in r.text


async def test_la_sesion_del_aprendiz_no_expone_la_propuesta(
    cliente, token_de, aprendiz_a, sesion_pendiente
):
    r = await cliente.get(
        f"/sesiones/{sesion_pendiente.id}", headers=token_de(aprendiz_a)
    )

    assert r.status_code == 200
    assert "puntuaciones_agente" not in r.json()


# --------------------------------------------------------------------------- #
# El instructor revisa y confirma
# --------------------------------------------------------------------------- #

async def test_el_instructor_ve_transcripcion_y_propuesta(
    cliente, token_de, docente_a, sesion_pendiente
):
    r = await cliente.get(
        f"/sesiones/{sesion_pendiente.id}/revision", headers=token_de(docente_a)
    )

    assert r.status_code == 200
    datos = r.json()
    assert datos["puntuaciones_agente"]["Seguridad"] == 3
    assert datos["nota_propuesta"] == pytest.approx(64.5)


async def test_confirmar_publica_la_nota_y_registra_las_diferencias(
    cliente, token_de, docente_a, aprendiz_a, sesion_pendiente
):
    r = await cliente.post(
        f"/sesiones/{sesion_pendiente.id}/revision",
        headers=token_de(docente_a),
        json={
            "puntuaciones_finales": {
                "Endpoints": 8,
                "Manejo de errores": 6,
                "Diseño": 7,
                "Seguridad": 5,
                "Explicación": 9,
            },
            "retroalimentacion": "Explicas bien el flujo. Refuerza los códigos de estado.",
        },
    )

    assert r.status_code == 200
    datos = r.json()
    assert datos["estado"] == "CALIFICADA"
    assert datos["aprobado"] is True
    # Evidencia de supervisión humana efectiva (KPIs K4 y K5).
    assert datos["diferencias_con_agente"] == {
        "Seguridad": {"agente": 3, "final": 5},
        "Explicación": {"agente": 7, "final": 9},
    }

    # Solo ahora el aprendiz ve su nota.
    resultados = await cliente.get("/mis-resultados", headers=token_de(aprendiz_a))
    publicado = resultados.json()[0]
    assert publicado["estado"] == "CALIFICADA"
    assert publicado["nota_final"] == datos["nota_final"]
    assert publicado["retroalimentacion"].startswith("Explicas bien")


async def test_un_docente_de_otra_ficha_no_puede_confirmar(
    cliente, token_de, docente_b, sesion_pendiente
):
    r = await cliente.post(
        f"/sesiones/{sesion_pendiente.id}/revision",
        headers=token_de(docente_b),
        json={"puntuaciones_finales": {"Endpoints": 10}},
    )

    assert r.status_code == 404


async def test_las_puntuaciones_deben_cubrir_la_rubrica_completa(
    cliente, token_de, docente_a, sesion_pendiente
):
    r = await cliente.post(
        f"/sesiones/{sesion_pendiente.id}/revision",
        headers=token_de(docente_a),
        json={"puntuaciones_finales": {"Endpoints": 8}},
    )

    assert r.status_code == 422
    assert "Faltan" in r.json()["detail"]


async def test_puntuacion_fuera_de_rango(cliente, token_de, docente_a, sesion_pendiente):
    r = await cliente.post(
        f"/sesiones/{sesion_pendiente.id}/revision",
        headers=token_de(docente_a),
        json={"puntuaciones_finales": {"Endpoints": 47}},
    )
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Cálculo ponderado (T-010)
# --------------------------------------------------------------------------- #

def test_la_nota_respeta_los_pesos_de_la_rubrica():
    """Caso aritmético del ticket T-010: 40/30/30 con 8/6/10 da 80 %."""
    rubrica = {
        "criterios": [
            {"nombre": "A", "peso": 40},
            {"nombre": "B", "peso": 30},
            {"nombre": "C", "peso": 30},
        ]
    }
    nota = calcular_nota({"A": 8, "B": 6, "C": 10}, rubrica)

    assert nota == pytest.approx(80.0)


def test_criterio_ausente_puntua_cero():
    rubrica = {"criterios": [{"nombre": "A", "peso": 50}, {"nombre": "B", "peso": 50}]}
    assert calcular_nota({"A": 10}, rubrica) == pytest.approx(50.0)


# --------------------------------------------------------------------------- #
# La garantía estructural
# --------------------------------------------------------------------------- #

def test_solo_el_servicio_de_revision_puede_calificar():
    """Criterio de aceptación central de T-011.

    Verifica por inspección del árbol sintáctico que la única asignación de
    `EstadoSesion.CALIFICADA` en todo `app/` está dentro de
    `ServicioRevision.confirmar`. Un test funcional no basta: probaría los
    caminos que conocemos, no la ausencia de otros.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent / "app"
    fuera_de_confirmar: list[str] = []
    encontradas = 0

    for fichero in sorted(raiz.rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))

        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Assign) or not _es_calificada(nodo.value):
                continue
            encontradas += 1
            if not _dentro_de_confirmar(arbol, nodo):
                fuera_de_confirmar.append(f"{fichero.relative_to(raiz)}:{nodo.lineno}")

    assert not fuera_de_confirmar, (
        "Hay asignaciones de EstadoSesion.CALIFICADA fuera de "
        f"ServicioRevision.confirmar: {fuera_de_confirmar}. "
        "Ninguna nota puede publicarse sin confirmación humana (ADR-006)."
    )
    assert encontradas == 1, (
        f"Se esperaba exactamente una asignación de CALIFICADA y hay {encontradas}. "
        "Si es intencionado, revisa que sigue cumpliéndose el ADR-006."
    )


def _es_calificada(nodo: ast.expr) -> bool:
    return (
        isinstance(nodo, ast.Attribute)
        and nodo.attr == "CALIFICADA"
        and isinstance(nodo.value, ast.Name)
        and nodo.value.id == "EstadoSesion"
    )


def _dentro_de_confirmar(arbol: ast.Module, objetivo: ast.Assign) -> bool:
    for nodo in ast.walk(arbol):
        es_funcion = isinstance(nodo, ast.AsyncFunctionDef | ast.FunctionDef)
        if es_funcion and nodo.name == "confirmar":
            if any(hijo is objetivo for hijo in ast.walk(nodo)):
                return True
    return False
