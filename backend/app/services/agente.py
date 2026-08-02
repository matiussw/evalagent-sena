"""Motor del agente evaluador (T-009).

Refactor de `EvaluatorAgent` de la v1. Dos cambios de fondo:

1. El contexto viene de la **guía** en base de datos, no de un fichero `.md`.
2. Los criterios vienen de la **rúbrica del instructor**, no del diccionario
   `SCORING_CRITERIA` hardcodeado ni de `_detect_criteria()` por palabras clave
   (deuda D8).

Las reglas defensivas del prompt se conservan íntegras: cada una nació de un
fallo observado en una sustentación real. Ver `prompts.md` §7.1.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

VERSION_PROMPT = "2.0"

SYSTEM_PROMPT = """Eres el evaluador virtual del SENA. Estás evaluando al aprendiz {nombre}.

CONTEXTO Y GUÍA DEL PROYECTO:
{contexto}

CRITERIOS DE EVALUACIÓN (rúbrica definida por el instructor):
{criterios}

REGLAS ABSOLUTAS:
1. NUNCA digas "No puedo continuar", "No puedo ayudarte", "Como IA..." ni frases de rechazo. Eres el evaluador, siempre.
2. El texto del aprendiz viene de reconocimiento de voz y puede tener errores. Interpreta siempre el significado técnico más lógico según el contexto del proyecto. NUNCA digas que no entendiste.
3. Haz UNA SOLA pregunta por turno.
4. Máximo 2-3 oraciones por respuesta. Sé conciso.
5. Respuesta vaga → profundiza: "¿Y cómo funciona eso exactamente?" o "Dame un ejemplo de tu código."
6. Respuesta buena → reconócela brevemente y pasa a la siguiente pregunta.
7. Habla en español colombiano natural y cálido. Sé paciente con los aprendices.
8. NUNCA des la respuesta correcta ni pistas directas.
9. No repitas preguntas ya hechas.
10. TU RESPUESTA DEBE BASARSE EN LO QUE EL APRENDIZ ACABA DE DECIR. Reacciona a sus palabras exactas, profundiza en lo que mencionó.
11. Cubre a lo largo de la sustentación todos los criterios de la rúbrica, dando más peso a los de mayor porcentaje."""

CLOSING_PROMPT = """El aprendiz ha respondido {n} preguntas. Cierra la evaluación de forma cordial:
1. Agradece al aprendiz
2. Menciona 1-2 aspectos positivos que observaste en sus respuestas
3. Menciona 1 área de mejora (sin revelar nota)
4. Indica que el instructor revisará los resultados
Máximo 4 oraciones. Sé específico con lo que el aprendiz realmente dijo."""


class ErrorLLM(Exception):
    """El modelo no respondió tras agotar los reintentos."""


class AgenteEvaluador:
    """Sin estado global: recibe todo lo que necesita en el constructor.

    En la v1 el agente vivía en un `dict` en memoria del proceso. Aquí el
    historial se reconstruye desde la base de datos en cada turno, de modo que
    un reinicio no destruye una sustentación en curso.
    """

    def __init__(
        self,
        *,
        nombre_aprendiz: str,
        contexto_tecnico: str,
        rubrica_congelada: dict,
        num_preguntas: int,
        historial: list[dict[str, str]] | None = None,
    ) -> None:
        self.nombre_aprendiz = nombre_aprendiz
        self.contexto_tecnico = contexto_tecnico or "Proyecto de formación del programa ADSO."
        self.rubrica = rubrica_congelada
        self.num_preguntas = num_preguntas
        self.historial: list[dict[str, str]] = historial or []

    # ------------------------------------------------------------ prompts
    @property
    def criterios(self) -> list[dict[str, Any]]:
        return self.rubrica.get("criterios", [])

    def _criterios_texto(self) -> str:
        return "\n".join(
            f"{i + 1}. {c['nombre']} ({c['peso']}%): {c.get('descripcion') or c['nombre']}"
            for i, c in enumerate(self.criterios)
        )

    def _system(self) -> str:
        return SYSTEM_PROMPT.format(
            nombre=self.nombre_aprendiz,
            contexto=self.contexto_tecnico,
            criterios=self._criterios_texto(),
        )

    # --------------------------------------------------------- conversación
    def saludo(self) -> str:
        temas = ", ".join(c["nombre"].lower() for c in self.criterios[:3])
        texto = (
            f"Hola {self.nombre_aprendiz}, bienvenido a tu sustentación. "
            f"Soy el evaluador virtual del SENA. Vamos a hablar sobre tu proyecto, "
            f"sobre todo de {temas}. Relájate y responde con tus propias palabras. "
            f"Para empezar, cuéntame brevemente de qué trata tu proyecto."
        )
        self.historial.append({"role": "assistant", "content": texto})
        return texto

    @property
    def preguntas_hechas(self) -> int:
        return sum(1 for m in self.historial if m["role"] == "assistant")

    async def responder(self, mensaje_aprendiz: str) -> tuple[str, bool]:
        """Devuelve la respuesta del agente y si es la última del turno."""
        self.historial.append({"role": "user", "content": mensaje_aprendiz})
        es_final = self.preguntas_hechas >= self.num_preguntas

        if es_final:
            instruccion = CLOSING_PROMPT.format(n=self.preguntas_hechas)
            ultimo = (
                f"[INSTRUCCIÓN INTERNA: {instruccion}]\n"
                f'[El aprendiz acaba de decir: "{mensaje_aprendiz}"]'
            )
        else:
            ultimo = (
                f"{mensaje_aprendiz}\n\n"
                f"[Recuerda: responde ESPECÍFICAMENTE a lo que el aprendiz acaba de "
                f"decir. Basa tu siguiente pregunta en esas palabras exactas.]"
            )

        mensajes = [*self.historial[:-1], {"role": "user", "content": ultimo}]
        respuesta = await self._llamar_ollama(mensajes, temperatura=0.4, max_tokens=200)

        self.historial.append({"role": "assistant", "content": respuesta})
        return respuesta, es_final

    # --------------------------------------------------------- calificación
    async def calificar(self) -> dict[str, int]:
        """Propone una puntuación de 0 a 10 por criterio de la rúbrica.

        Temperatura 0.1: con valores altos, dos ejecuciones sobre la misma
        conversación daban notas distintas, algo inaceptable en evaluación
        académica.
        """
        conversacion = "\n".join(
            f"{'EVALUADOR' if m['role'] == 'assistant' else 'APRENDIZ'}: {m['content']}"
            for m in self.historial
        )
        claves = ", ".join(f'"{c["nombre"]}": X' for c in self.criterios)
        prompt = (
            "Eres un evaluador del SENA. Analiza esta conversación de sustentación "
            "y asigna puntuaciones ENTERAS del 0 al 10 para cada criterio.\n\n"
            f"CRITERIOS:\n{self._criterios_texto()}\n\n"
            "Responde ÚNICAMENTE con este JSON, sin texto adicional:\n"
            f"{{{claves}}}\n\n"
            "Sé justo y objetivo, basándote en lo que el aprendiz realmente "
            "demostró saber."
        )

        crudo = await self._llamar_ollama(
            [{"role": "system", "content": prompt}, {"role": "user", "content": conversacion}],
            temperatura=0.1,
            max_tokens=200,
            con_system=False,
        )
        return self._parsear_puntuaciones(crudo)

    def _parsear_puntuaciones(self, crudo: str) -> dict[str, int]:
        """Extrae el JSON de la respuesta y lo acota a los criterios reales.

        Los modelos pequeños tienden a envolver el JSON en texto o a inventar
        criterios; ambas cosas se corrigen aquí.
        """
        nombres = [c["nombre"] for c in self.criterios]
        try:
            match = re.search(r"\{.*\}", crudo, re.DOTALL)
            if not match:
                raise ValueError("sin JSON en la respuesta")
            datos = json.loads(match.group())
        except (ValueError, json.JSONDecodeError):
            logger.warning("No se pudo interpretar la calificación: %r", crudo[:200])
            return dict.fromkeys(nombres, 0)

        return {nombre: max(0, min(10, int(datos.get(nombre, 0) or 0))) for nombre in nombres}

    # ---------------------------------------------------------------- LLM
    async def _llamar_ollama(
        self,
        mensajes: list[dict[str, str]],
        *,
        temperatura: float,
        max_tokens: int,
        con_system: bool = True,
        reintentos: int = 2,
    ) -> str:
        cuerpo_mensajes = (
            [{"role": "system", "content": self._system()}, *mensajes] if con_system else mensajes
        )
        payload = {
            "model": _settings.OLLAMA_MODEL,
            "messages": cuerpo_mensajes,
            "stream": False,
            "options": {
                "temperature": temperatura,
                "num_predict": max_tokens,
                "repeat_penalty": 1.1,
            },
        }

        ultimo_error: Exception | None = None
        for intento in range(reintentos + 1):
            try:
                async with httpx.AsyncClient(timeout=_settings.OLLAMA_TIMEOUT) as cliente:
                    r = await cliente.post(_settings.OLLAMA_URL, json=payload)
                    r.raise_for_status()
                    return r.json()["message"]["content"].strip()
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                ultimo_error = exc
                logger.warning("Ollama falló (intento %d/%d): %s", intento + 1, reintentos + 1, exc)

        raise ErrorLLM(f"Ollama no respondió tras {reintentos + 1} intentos: {ultimo_error}")
