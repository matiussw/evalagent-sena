# T-007 · Ciclo de vida de la sesión de sustentación

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-08](../02-backlog/02-historias-usuario.md#hu-08--iniciar-una-sustentación-desde-la-guía) |
| **Épica** | E3 · Sustentación por voz |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/models/sesion.py` · `backend/app/api/v1/sesiones.py` |
| **Estado** | `Por hacer` |

## Descripción

Modelar la sesión como una máquina de estados persistida. En la versión 1 el estado vivía
en un `dict` en memoria y se perdía en cada reinicio (deuda **D7**); aquí pasa a base de
datos, lo que además habilita la reanudación (HU-10) y la auditoría.

## Máquina de estados

```
INICIADA → EN_CURSO → PENDIENTE_REVISION → CALIFICADA → EN_RECLAMACION
    └──────────────→ ABANDONADA
```

## Alcance técnico

- Modelo `Sesion`: `guia_id`, `aprendiz_id`, `estado`, `iniciada_en`, `finalizada_en`,
  `preguntas_respondidas`, `consentimiento_aceptado_en`, `ultimo_latido`.
- Modelo `TurnoConversacion`: `sesion_id`, `orden`, `rol` (`AGENTE`/`APRENDIZ`),
  `contenido`, `creado_en`. **No se guarda el audio, solo el texto** (RNF-09).
- `POST /api/v1/sesiones` → crea la sesión y devuelve el ticket del WebSocket.
- `GET /api/v1/sesiones/{id}` → estado y turnos.
- Validaciones: inscripción activa, guía publicada, dentro de ventana, sin sesión previa
  completada, consentimiento aceptado.

## Criterios de aceptación

- [ ] Iniciar sin inscripción activa devuelve `403`.
- [ ] Iniciar fuera de la ventana devuelve `403` con "La ventana de sustentación está cerrada".
- [ ] Segundo intento sobre una guía ya completada devuelve `409`.
- [ ] Sin `consentimiento_aceptado_en` la sesión no se crea (`422`).
- [ ] Una sesión sin latido durante 60 min pasa a `ABANDONADA` mediante tarea programada.
- [ ] En la base de datos no existe ninguna columna ni fichero con audio crudo.

## Definición de terminado

Transiciones de estado cubiertas por tests · tarea de expiración probada · RNF-09 verificado.

## Dependencias

**Requiere:** T-006. **Bloquea:** T-008.
