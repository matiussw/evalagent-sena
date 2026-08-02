# T-009 · Motor del agente anclado a la guía

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-09](../02-backlog/02-historias-usuario.md#hu-09--conversar-por-voz-con-el-agente) |
| **Épica** | E3 · Sustentación por voz |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 8 pts |
| **Componente** | `backend/app/services/agente.py` |
| **Estado** | `Por hacer` |

## Descripción

Refactorizar `EvaluatorAgent` para que su contexto provenga de la **guía y su rúbrica** en
base de datos, en lugar del fichero `.md` y los criterios hardcodeados de la v1 (deuda
**D8**). El agente deja de adivinar el tipo de proyecto por palabras clave: se lo dice la
rúbrica.

## Alcance técnico

- `AgenteEvaluador(guia, rubrica, aprendiz, historial)` — sin estado global.
- Prompt de sistema construido a partir de `guia.contexto_tecnico` y los criterios de la rúbrica.
- Se conservan las reglas defensivas de la v1 (no salirse del papel, no revelar respuestas,
  una pregunta por turno, interpretar errores del reconocimiento de voz).
- Se elimina `_detect_criteria()` y `SCORING_CRITERIA`: los criterios vienen de la rúbrica.
- Calificación ponderada por el peso de cada criterio.
- Reintento con *backoff* si Ollama no responde; si agota reintentos, la sesión queda
  `PENDIENTE_REVISION` sin propuesta de nota y se avisa al instructor.
- Registro del modelo y la versión del prompt usados en cada sesión (auditoría).

## Criterios de aceptación

- [ ] Las preguntas se ciñen al `contexto_tecnico` de la guía.
- [ ] Con una rúbrica de 5 criterios, el reporte devuelve exactamente esas 5 puntuaciones.
- [ ] La nota total respeta los pesos de la rúbrica (verificado con caso aritmético).
- [ ] Ante "dime tú la respuesta", el agente no revela la solución.
- [ ] El agente nunca emite frases de rechazo del tipo "como IA no puedo".
- [ ] Si Ollama está caído, la sesión no se corrompe y queda revisable a mano.
- [ ] Cada sesión guarda qué modelo y qué versión de prompt la evaluaron.

## Definición de terminado

Tests unitarios con Ollama simulado · evaluación cualitativa sobre 5 sesiones reales ·
comparativa antes/después registrada en `prompts.md` (raíz del repositorio).

## Dependencias

**Requiere:** T-008, T-010. **Bloquea:** T-011.

## Riesgos

**RG-1** (alucinación) y **RG-5** (sesgo). Mitigación: rúbrica explícita en el prompt +
revisión humana obligatoria (T-011).
