# ADR-006 · Confirmación humana obligatoria de toda calificación

**Estado:** ✅ Aceptada · **Fecha:** 2026-08-02 · **Carácter:** innegociable

## Contexto

El sistema propone una calificación académica a partir de una conversación. Una nota tiene
efectos significativos sobre una persona: condiciona su avance en el programa y, en última
instancia, su certificación.

El marco normativo es explícito:

- **Art. 22 del RGPD** (referencia internacional): derecho a no ser objeto de una decisión
  basada únicamente en tratamiento automatizado que produzca efectos jurídicos o
  significativos.
- **AI Act (UE)**: los sistemas de IA usados para evaluar resultados de aprendizaje son de
  **alto riesgo**, y exigen supervisión humana efectiva.
- **Ley 1581/2012 (Colombia)**: derecho del titular a conocer, actualizar y rectificar.

Añadido a esto, un LLM de 8B parámetros comete errores de juicio: puede penalizar una
respuesta correcta expresada con vocabulario informal, o premiar una respuesta fluida pero
vacía. El riesgo **RG-5** (sesgo contra ciertas formas de hablar) es real y crítico.

## Decisión

**Ninguna calificación llega al aprendiz sin que un instructor la haya confirmado
explícitamente.**

Materialización en la arquitectura:

1. Al terminar la conversación, la sesión pasa a `PENDIENTE_REVISION`, **nunca** a `CALIFICADA`.
2. La propuesta del agente se guarda en `sesion.puntuaciones_agente` y **no se expone al
   aprendiz** en ningún endpoint mientras la sesión no esté `CALIFICADA`.
3. La transición a `CALIFICADA` requiere una fila en la tabla `revision` con `revisor_id`.
   Es una regla de integridad (**RI-4**), no una convención.
4. Se registra el diferencial entre la propuesta del agente y la nota final: es la evidencia
   de que hubo supervisión real y no un clic automático.
5. El aprendiz puede reclamar (`EN_RECLAMACION`), lo que materializa el derecho a impugnar.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Publicación automática con opción de revisión posterior | Es exactamente lo que prohíbe el Art. 22: la decisión ya produjo efecto antes de la supervisión. |
| Publicación automática solo si la nota supera un umbral alto | Sigue siendo decisión automatizada. Además, un aprobado injusto también es un error evaluativo. |
| Revisión por muestreo (revisar 1 de cada 5) | Reintroduce la arbitrariedad del muestreo que el producto vino a eliminar (problema P2). |

## Consecuencias

**Positivas**
- El sistema es legalmente admisible en un contexto educativo público.
- El instructor conserva su autoridad académica: el producto le devuelve tiempo, no se la quita.
- La comparación propuesta ↔ nota final alimenta el KPI **K4** y permite detectar sesgos
  sistemáticos del modelo (mitigación de **RG-5**).
- Reduce el rechazo de los aprendices a ser evaluados por IA (**RG-3**): la interfaz muestra
  explícitamente que decide una persona.

**Negativas**
- El ahorro de tiempo no es del 100 %: quedan ~3 min de revisión por sustentación.
  Es un coste asumido y explícito en el KPI **K2**.
- Introduce un cuello de botella si el instructor no revisa: las sesiones se acumulan en
  `PENDIENTE_REVISION`. Mitigación: bandeja de revisión con orden por antigüedad y aviso.

## Verificación

El criterio de aceptación más importante de T-011: **no debe existir ninguna ruta de código
que lleve una sesión a `CALIFICADA` sin pasar por el servicio de revisión.** Se valida por
búsqueda exhaustiva sobre el código, no solo con tests.
