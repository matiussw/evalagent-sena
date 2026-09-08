"""Tests del motor del agente (T-009).

Ollama se simula: la suite no puede depender de que haya un modelo cargado, y
menos aún de que responda lo mismo dos veces.
"""

from __future__ import annotations

import httpx
import pytest

from app.services.agente import AgenteEvaluador, ErrorLLM


@pytest.fixture
def rubrica_congelada() -> dict:
    return {
        "version_esquema": 1,
        "umbral_aprobacion": 60,
        "criterios": [
            {"nombre": "Endpoints", "descripcion": "Verbos HTTP y rutas", "peso": 40},
            {"nombre": "Seguridad", "descripcion": "Autenticación", "peso": 30},
            {"nombre": "Explicación", "descripcion": "Claridad", "peso": 30},
        ],
    }


@pytest.fixture
def agente(rubrica_congelada) -> AgenteEvaluador:
    return AgenteEvaluador(
        nombre_aprendiz="Jhon",
        contexto_tecnico="API REST con Node.js. Temas: endpoints, códigos HTTP y JWT.",
        rubrica_congelada=rubrica_congelada,
        num_preguntas=3,
    )


def _simular_ollama(monkeypatch, respuestas: list[str]) -> list[dict]:
    """Sustituye el cliente HTTP y devuelve las cargas útiles enviadas."""
    enviados: list[dict] = []
    pendientes = list(respuestas)

    class ClienteSimulado:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def post(self, _url, json):
            enviados.append(json)
            contenido = pendientes.pop(0) if pendientes else ""
            return httpx.Response(
                200, json={"message": {"content": contenido}}, request=httpx.Request("POST", _url)
            )

    monkeypatch.setattr("app.services.agente.httpx.AsyncClient", ClienteSimulado)
    return enviados


# --------------------------------------------------------------------------- #
# El prompt se construye desde la guía y la rúbrica
# --------------------------------------------------------------------------- #


def test_el_prompt_incluye_el_contexto_de_la_guia(agente):
    assert "API REST con Node.js" in agente._system()


def test_el_prompt_incluye_los_criterios_con_su_peso(agente):
    system = agente._system()

    assert "Endpoints (40%)" in system
    assert "Seguridad (30%)" in system
    assert "Explicación (30%)" in system


def test_el_prompt_conserva_las_reglas_defensivas(agente):
    """Cada regla nació de un fallo real con aprendices. No deben perderse."""
    system = agente._system()

    assert "NUNCA digas" in system
    assert "reconocimiento de voz" in system
    assert "UNA SOLA pregunta" in system
    assert "NUNCA des la respuesta correcta" in system


def test_los_criterios_ya_no_se_adivinan_por_palabras_clave(rubrica_congelada):
    """La v1 elegía criterios buscando 'python' o 'api' en el texto (deuda D8)."""
    agente = AgenteEvaluador(
        nombre_aprendiz="Jhon",
        contexto_tecnico="Proyecto de Python con variables, ciclos y funciones",
        rubrica_congelada=rubrica_congelada,
        num_preguntas=3,
    )

    # Pese a hablar de Python, los criterios son los que fijó el instructor.
    assert [c["nombre"] for c in agente.criterios] == [
        "Endpoints",
        "Seguridad",
        "Explicación",
    ]


# --------------------------------------------------------------------------- #
# Conversación
# --------------------------------------------------------------------------- #


def test_el_saludo_menciona_al_aprendiz_y_los_temas(agente):
    saludo = agente.saludo()

    assert "Jhon" in saludo
    assert "endpoints" in saludo.lower()
    assert agente.preguntas_hechas == 1


async def test_responder_encadena_el_historial(agente, monkeypatch):
    enviados = _simular_ollama(monkeypatch, ["¿Y cómo proteges esos endpoints?"])
    agente.saludo()

    respuesta, es_final = await agente.responder("Hice una API de tareas con Express")

    assert respuesta == "¿Y cómo proteges esos endpoints?"
    assert es_final is False
    # El último mensaje enviado recuerda al modelo que reaccione a esas palabras.
    ultimo = enviados[0]["messages"][-1]["content"]
    assert "Hice una API de tareas con Express" in ultimo
    assert "ESPECÍFICAMENTE" in ultimo


async def test_la_ultima_pregunta_activa_el_cierre(agente, monkeypatch):
    _simular_ollama(monkeypatch, ["pregunta 2", "pregunta 3", "Gracias Jhon, buen trabajo."])
    agente.saludo()

    await agente.responder("respuesta 1")
    await agente.responder("respuesta 2")
    respuesta, es_final = await agente.responder("respuesta 3")

    assert es_final is True
    assert "Gracias" in respuesta


async def test_el_cierre_pide_no_revelar_la_nota(agente, monkeypatch):
    enviados = _simular_ollama(monkeypatch, ["p2", "p3", "cierre"])
    agente.saludo()
    await agente.responder("r1")
    await agente.responder("r2")

    await agente.responder("r3")

    instruccion = enviados[-1]["messages"][-1]["content"]
    assert "sin revelar nota" in instruccion
    assert "el instructor revisará los resultados" in instruccion.lower()


# --------------------------------------------------------------------------- #
# Calificación
# --------------------------------------------------------------------------- #


async def test_calificar_devuelve_una_puntuacion_por_criterio(agente, monkeypatch):
    _simular_ollama(monkeypatch, ['{"Endpoints": 8, "Seguridad": 5, "Explicación": 9}'])

    puntuaciones = await agente.calificar()

    assert puntuaciones == {"Endpoints": 8, "Seguridad": 5, "Explicación": 9}


async def test_calificar_usa_temperatura_baja(agente, monkeypatch):
    """Con temperatura alta, dos ejecuciones daban notas distintas."""
    enviados = _simular_ollama(monkeypatch, ['{"Endpoints": 5, "Seguridad": 5, "Explicación": 5}'])

    await agente.calificar()

    assert enviados[0]["options"]["temperature"] == 0.1


async def test_calificar_extrae_el_json_envuelto_en_texto(agente, monkeypatch):
    """Los modelos pequeños suelen añadir prosa alrededor del JSON."""
    _simular_ollama(
        monkeypatch,
        [
            'Claro, aquí tienes:\n{"Endpoints": 7, "Seguridad": 4, "Explicación": 6}\n¡Espero que sirva!'
        ],
    )

    puntuaciones = await agente.calificar()

    assert puntuaciones == {"Endpoints": 7, "Seguridad": 4, "Explicación": 6}


async def test_calificar_descarta_criterios_inventados(agente, monkeypatch):
    """El modelo a veces añade criterios que no están en la rúbrica."""
    _simular_ollama(
        monkeypatch,
        ['{"Endpoints": 8, "Seguridad": 5, "Explicación": 9, "Simpatía": 10}'],
    )

    puntuaciones = await agente.calificar()

    assert "Simpatía" not in puntuaciones
    assert set(puntuaciones) == {"Endpoints", "Seguridad", "Explicación"}


async def test_calificar_acota_las_puntuaciones_al_rango(agente, monkeypatch):
    _simular_ollama(monkeypatch, ['{"Endpoints": 47, "Seguridad": -3, "Explicación": 9}'])

    puntuaciones = await agente.calificar()

    assert puntuaciones == {"Endpoints": 10, "Seguridad": 0, "Explicación": 9}


async def test_calificar_sin_json_no_revienta(agente, monkeypatch):
    """Una respuesta ininteligible no debe romper el cierre de la sesión."""
    _simular_ollama(monkeypatch, ["No estoy seguro de poder calificar esto."])

    puntuaciones = await agente.calificar()

    assert puntuaciones == {"Endpoints": 0, "Seguridad": 0, "Explicación": 0}


async def test_criterio_ausente_en_la_respuesta_puntua_cero(agente, monkeypatch):
    _simular_ollama(monkeypatch, ['{"Endpoints": 8}'])

    puntuaciones = await agente.calificar()

    assert puntuaciones == {"Endpoints": 8, "Seguridad": 0, "Explicación": 0}


# --------------------------------------------------------------------------- #
# Resiliencia
# --------------------------------------------------------------------------- #


async def test_ollama_caido_lanza_error_tras_reintentar(agente, monkeypatch):
    intentos = {"n": 0}

    class ClienteRoto:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def post(self, *_, **__):
            intentos["n"] += 1
            raise httpx.ConnectError("conexión rechazada")

    monkeypatch.setattr("app.services.agente.httpx.AsyncClient", ClienteRoto)
    agente.saludo()

    with pytest.raises(ErrorLLM, match="no respondió"):
        await agente.responder("hola")

    assert intentos["n"] == 3, "debe reintentar dos veces antes de rendirse"


def test_reconstruir_desde_el_historial_persistido(rubrica_congelada):
    """Un reinicio del servidor no puede destruir una sustentación en curso."""
    historial = [
        {"role": "assistant", "content": "Hola Jhon, cuéntame de tu proyecto"},
        {"role": "user", "content": "Es una API de tareas"},
        {"role": "assistant", "content": "¿Qué endpoints tiene?"},
    ]

    agente = AgenteEvaluador(
        nombre_aprendiz="Jhon",
        contexto_tecnico="API REST",
        rubrica_congelada=rubrica_congelada,
        num_preguntas=8,
        historial=historial,
    )

    assert agente.preguntas_hechas == 2
