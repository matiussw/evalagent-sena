# T-008 · Canal WebSocket de voz autenticado

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-09](../02-backlog/02-historias-usuario.md#hu-09--conversar-por-voz-con-el-agente) |
| **Épica** | E3 · Sustentación por voz |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/v1/ws.py` · `backend/app/services/stt.py` |
| **Estado** | `Por hacer` |

## Descripción

Reescribir el WebSocket de la versión 1 para que trabaje sobre el nuevo dominio. El cambio
de fondo es la **autenticación**: en la v1 cualquiera que adivinara un `session_id` podía
conectarse. Ahora el canal exige un ticket firmado y de un solo uso.

## Alcance técnico

- `WS /api/v1/ws/sesiones/{sesion_id}?ticket=<jwt>`.
- Ticket JWT de vida corta (60 s), un solo uso, ligado a `sesion_id` y `aprendiz_id`.
- Mensajes entrantes: `audio_chunk` (base64 + `mime_type`), `latido`, `finalizar`.
- Mensajes salientes: `transcripcion_aprendiz`, `mensaje_agente`, `transcripcion_vacia`,
  `evaluacion_completa`, `error`.
- Transcripción con `faster-whisper` en un *thread pool* para no bloquear el bucle de eventos.
- El fichero temporal de audio se borra en un `finally`, pase lo que pase.
- Cada turno se persiste en `TurnoConversacion` **antes** de responder.
- Límite de tamaño por fragmento de audio: 10 MB.

## Criterios de aceptación

- [ ] Conectar sin ticket cierra la conexión con código `4401`.
- [ ] Un ticket de otro aprendiz cierra con `4403`.
- [ ] Reutilizar un ticket ya consumido cierra con `4401`.
- [ ] Un audio con voz devuelve `transcripcion_aprendiz` en menos de 4 s (RNF-01).
- [ ] Un audio silencioso devuelve `transcripcion_vacia` y **no** consume pregunta.
- [ ] Los ficheros temporales se eliminan incluso si la transcripción lanza excepción.
- [ ] Un fragmento de más de 10 MB se rechaza sin tumbar la conexión.
- [ ] Al reconectar, los turnos previos siguen en base de datos.

## Definición de terminado

Tests con cliente WebSocket de prueba · latencia p95 medida · sin fugas de ficheros temporales.

## Dependencias

**Requiere:** T-007. **Bloquea:** T-009.
