# ADR-004 · WebSocket con audio por turnos en lugar de WebRTC continuo

**Estado:** ✅ Aceptada · **Fecha:** 2026-07-26

## Contexto

La sustentación es una conversación hablada. Hay dos formas de llevar audio del navegador al
servidor: un flujo continuo en tiempo real (WebRTC) o fragmentos discretos por turno
(WebSocket + `MediaRecorder`).

## Decisión

**WebSocket con fragmentos de audio por turno.** El aprendiz pulsa para hablar, suelta, y el
fragmento completo viaja en base64 por el canal WebSocket.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| **WebRTC con transcripción en flujo** | Latencia mucho menor y sensación de conversación natural. Descartada porque exige servidor TURN/STUN, gestión de sesiones de medios y transcripción por streaming — semanas de trabajo adicional para un proyecto de ~30 h. |
| **Subida de fichero por HTTP por cada turno** | Más simple, pero pierde el canal bidireccional que permite al servidor empujar estados ("transcribiendo", "pensando") sin *polling*. |

## Consecuencias

**Positivas**
- El navegador solo necesita `MediaRecorder` y `WebSocket`: cero dependencias externas.
- Los turnos discretos encajan con la naturaleza del dominio — es una sustentación con
  preguntas y respuestas, no una charla informal.
- El servidor puede empujar estados intermedios a la interfaz.
- Un fragmento perdido afecta a un turno, no a toda la sesión.

**Negativas**
- Latencia perceptible entre soltar el botón y oír la respuesta (objetivo p95 ≤ 6 s, RNF-01).
- No permite interrumpir al agente mientras habla.
- El audio base64 pesa un 33 % más que el binario. Mitigación: límite de 10 MB por fragmento.

## Nota de evolución

Si en la práctica la latencia resulta inaceptable, el siguiente paso no es WebRTC sino
**transcripción por streaming sobre el mismo WebSocket** (enviar fragmentos parciales
mientras el aprendiz habla). Conserva la arquitectura y recorta la espera.
