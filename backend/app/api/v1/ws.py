"""Canal WebSocket de la sustentación (T-008).

Cambio de fondo respecto a la v1: el canal está **autenticado**. Antes bastaba
con adivinar un `session_id` para conectarse a la sustentación de cualquiera.
Ahora exige un ticket firmado, de un solo uso, ligado a la sesión y al aprendiz.
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import tempfile
import time
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import ErrorToken, decodificar_token
from app.db.session import SesionAsync
from app.models.enums import EstadoSesion, RolTurno
from app.models.identidad import Usuario
from app.models.sustentacion import Sesion
from app.services import stt, tts
from app.services.agente import VERSION_PROMPT, AgenteEvaluador, ErrorLLM
from app.services.sesion import ServicioSesion

logger = logging.getLogger(__name__)
_settings = get_settings()
router = APIRouter(tags=["Sustentación"])

# Códigos de cierre documentados en la especificación de la API.
CIERRE_NO_AUTORIZADO = 4401
CIERRE_PROHIBIDO = 4403
CIERRE_ESTADO_INVALIDO = 4409
CIERRE_ERROR_INTERNO = 1011

# Tickets ya consumidos. En memoria: basta para una instancia única, que es el
# modelo de despliegue previsto (una por centro de formación).
_tickets_usados: set[str] = set()

_EXTENSIONES = {"mp4": ".mp4", "ogg": ".ogg", "webm": ".webm"}


@router.websocket("/ws/sesiones/{sesion_id}")
async def canal_sustentacion(
    websocket: WebSocket,
    sesion_id: uuid.UUID,
    ticket: str = Query(default=""),
) -> None:
    await websocket.accept()

    payload = _validar_ticket(ticket, sesion_id)
    if payload is None:
        await websocket.close(code=CIERRE_NO_AUTORIZADO, reason="Ticket inválido")
        return

    _tickets_usados.add(payload["jti"])
    aprendiz_id = uuid.UUID(payload["sub"])

    async with SesionAsync() as bd:
        try:
            contexto = await _cargar_contexto(bd, sesion_id, aprendiz_id)
        except _CanalNoValido as exc:
            await websocket.close(code=exc.codigo, reason=exc.motivo)
            return

        sesion, aprendiz, servicio = contexto
        agente = _construir_agente(sesion, aprendiz)

        try:
            await _saludar(websocket, agente, sesion, servicio, bd)
            await _bucle_conversacion(websocket, agente, sesion, servicio, bd)
        except WebSocketDisconnect:
            # Desconexión normal. El estado queda en base de datos, así que el
            # aprendiz puede reanudar donde iba (HU-10).
            logger.info("Aprendiz desconectado de la sesión %s", sesion_id)
            await bd.commit()
        except ErrorLLM:
            logger.exception("Ollama no respondió en la sesión %s", sesion_id)
            await _enviar(
                websocket,
                {
                    "type": "error",
                    "codigo": "llm_no_disponible",
                    "mensaje": "El evaluador no está disponible. Tu progreso se guardó; "
                    "avisa a tu instructor.",
                },
            )
            await bd.commit()
            await websocket.close(code=CIERRE_ERROR_INTERNO)
        except Exception:
            logger.exception("Fallo inesperado en la sesión %s", sesion_id)
            await bd.rollback()
            await websocket.close(code=CIERRE_ERROR_INTERNO)


# --------------------------------------------------------------------------- #
# Validación y carga
# --------------------------------------------------------------------------- #


class _CanalNoValido(Exception):
    def __init__(self, codigo: int, motivo: str) -> None:
        self.codigo = codigo
        self.motivo = motivo
        super().__init__(motivo)


def _validar_ticket(ticket: str, sesion_id: uuid.UUID) -> dict | None:
    if not ticket:
        return None
    try:
        payload = decodificar_token(ticket, tipo_esperado="ws_ticket")
    except ErrorToken:
        return None

    jti = payload.get("jti")
    if not jti or jti in _tickets_usados:
        return None
    if payload.get("sid") != str(sesion_id):
        return None
    return payload


async def _cargar_contexto(
    bd: AsyncSession, sesion_id: uuid.UUID, aprendiz_id: uuid.UUID
) -> tuple[Sesion, Usuario, ServicioSesion]:
    aprendiz = await bd.get(Usuario, aprendiz_id)
    if aprendiz is None or not aprendiz.activo:
        raise _CanalNoValido(CIERRE_PROHIBIDO, "Cuenta inválida")

    servicio = ServicioSesion(bd, aprendiz.institucion_id)
    sesion = await servicio.sesiones.con_turnos(sesion_id)

    if sesion is None or sesion.aprendiz_id != aprendiz_id:
        raise _CanalNoValido(CIERRE_PROHIBIDO, "La sesión no es tuya")

    if sesion.estado not in (EstadoSesion.INICIADA, EstadoSesion.EN_CURSO):
        raise _CanalNoValido(CIERRE_ESTADO_INVALIDO, f"La sesión está en estado {sesion.estado}")

    return sesion, aprendiz, servicio


def _construir_agente(sesion: Sesion, aprendiz: Usuario) -> AgenteEvaluador:
    """Reconstruye el agente desde la base de datos.

    En la v1 el agente vivía en un `dict` del proceso y un reinicio destruía la
    sustentación (deuda D7). Aquí el historial se recupera de los turnos.
    """
    historial = [
        {
            "role": "assistant" if t.rol == RolTurno.AGENTE else "user",
            "content": t.contenido,
        }
        for t in sesion.turnos
    ]
    return AgenteEvaluador(
        nombre_aprendiz=aprendiz.nombre,
        contexto_tecnico=sesion.guia.contexto_tecnico or "",
        rubrica_congelada=sesion.rubrica_congelada,
        num_preguntas=sesion.guia.num_preguntas,
        historial=historial,
    )


# --------------------------------------------------------------------------- #
# Conversación
# --------------------------------------------------------------------------- #


async def _saludar(
    websocket: WebSocket,
    agente: AgenteEvaluador,
    sesion: Sesion,
    servicio: ServicioSesion,
    bd: AsyncSession,
) -> None:
    if agente.historial:
        # Reanudación: se reenvía el estado sin repetir el saludo.
        await _enviar(
            websocket,
            {
                "type": "sesion_reanudada",
                "pregunta_num": agente.preguntas_hechas,
                "total_preguntas": agente.num_preguntas,
                "turnos": [{"rol": t.rol.value, "contenido": t.contenido} for t in sesion.turnos],
            },
        )
        return

    saludo = agente.saludo()
    await servicio.registrar_turno(sesion, rol=RolTurno.AGENTE, contenido=saludo)
    await bd.commit()
    await _enviar(
        websocket,
        {
            "type": "mensaje_agente",
            "texto": saludo,
            "audio": await tts.sintetizar_voz(saludo),
            "pregunta_num": 1,
            "total_preguntas": agente.num_preguntas,
            "es_final": False,
        },
    )


async def _bucle_conversacion(
    websocket: WebSocket,
    agente: AgenteEvaluador,
    sesion: Sesion,
    servicio: ServicioSesion,
    bd: AsyncSession,
) -> None:
    while True:
        mensaje = await websocket.receive_json()
        tipo = mensaje.get("type")

        if tipo == "latido":
            await servicio.latido(sesion)
            await bd.commit()
            continue

        if tipo == "finalizar":
            await _cerrar(websocket, agente, sesion, servicio, bd)
            return

        if tipo != "audio_chunk":
            continue

        inicio = time.monotonic()
        texto = await _transcribir_mensaje(websocket, mensaje)
        if texto is None:
            continue

        await servicio.registrar_turno(sesion, rol=RolTurno.APRENDIZ, contenido=texto)
        await bd.commit()
        await _enviar(websocket, {"type": "transcripcion_aprendiz", "texto": texto})
        await _enviar(websocket, {"type": "estado_agente", "estado": "pensando"})

        respuesta, es_final = await agente.responder(texto)
        latencia = int((time.monotonic() - inicio) * 1000)

        await servicio.registrar_turno(
            sesion, rol=RolTurno.AGENTE, contenido=respuesta, latencia_ms=latencia
        )
        sesion.preguntas_respondidas = agente.preguntas_hechas
        await bd.commit()

        await _enviar(
            websocket,
            {
                "type": "mensaje_agente",
                "texto": respuesta,
                "audio": await tts.sintetizar_voz(respuesta),
                "pregunta_num": agente.preguntas_hechas,
                "total_preguntas": agente.num_preguntas,
                "es_final": es_final,
                "latencia_ms": latencia,
            },
        )

        if es_final:
            await _cerrar(websocket, agente, sesion, servicio, bd)
            return


async def _transcribir_mensaje(websocket: WebSocket, mensaje: dict) -> str | None:
    """Devuelve el texto reconocido, o None si no hay que consumir pregunta."""
    try:
        audio = base64.b64decode(mensaje.get("audio", ""), validate=True)
    except (binascii.Error, ValueError):
        await _enviar(
            websocket,
            {"type": "error", "codigo": "audio_invalido", "mensaje": "Audio ilegible"},
        )
        return None

    if len(audio) > _settings.MAX_AUDIO_BYTES:
        await _enviar(
            websocket,
            {
                "type": "error",
                "codigo": "audio_demasiado_grande",
                "mensaje": "El fragmento de audio supera el límite permitido",
            },
        )
        return None

    mime = mensaje.get("mime_type", "audio/webm")
    extension = next((ext for clave, ext in _EXTENSIONES.items() if clave in mime), ".webm")

    ruta = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(audio)
            ruta = tmp.name

        await _enviar(websocket, {"type": "estado_agente", "estado": "transcribiendo"})
        texto = await stt.transcribir(ruta)
    finally:
        # El audio crudo se descarta siempre: nunca se persiste (RNF-09).
        if ruta and os.path.exists(ruta):
            try:
                os.unlink(ruta)
            except OSError:
                logger.warning("No se pudo borrar el temporal de audio %s", ruta)

    if not texto.strip():
        await _enviar(websocket, {"type": "transcripcion_vacia"})
        return None
    return texto


async def _cerrar(
    websocket: WebSocket,
    agente: AgenteEvaluador,
    sesion: Sesion,
    servicio: ServicioSesion,
    bd: AsyncSession,
) -> None:
    """Cierra la sustentación.

    La sesión queda en PENDIENTE_REVISION y el mensaje de cierre **no lleva
    ninguna nota**: la propuesta del agente no se muestra jamás al aprendiz.
    """
    try:
        puntuaciones = await agente.calificar()
    except ErrorLLM:
        # Sin propuesta, pero la sesión sigue siendo revisable a mano.
        logger.exception("No se pudo calificar la sesión %s", sesion.id)
        puntuaciones = None

    await servicio.cerrar(
        sesion,
        puntuaciones_agente=puntuaciones,
        modelo_llm=_settings.OLLAMA_MODEL,
        version_prompt=VERSION_PROMPT,
    )
    await bd.commit()

    await _enviar(
        websocket,
        {
            "type": "evaluacion_completa",
            "sesion_id": str(sesion.id),
            "estado": EstadoSesion.PENDIENTE_REVISION.value,
            "mensaje": "Tu sustentación quedó registrada. Tu instructor revisará "
            "los resultados y publicará la nota.",
        },
    )


async def _enviar(websocket: WebSocket, datos: dict) -> None:
    try:
        await websocket.send_json(datos)
    except (WebSocketDisconnect, RuntimeError):
        raise WebSocketDisconnect(code=1000) from None
