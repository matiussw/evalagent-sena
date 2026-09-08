# ADR-007 · La sesión congela una copia de su rúbrica

**Estado:** ✅ Aceptada · **Fecha:** 2026-08-02

## Contexto

El instructor puede editar la rúbrica de una guía en cualquier momento: cambiar pesos, añadir
un criterio, reformular una descripción. Es deseable — la rúbrica mejora con la experiencia.

El problema aparece a mitad de trimestre: si 15 aprendices ya sustentaron con la rúbrica A y
el instructor la cambia a la rúbrica B, ¿con qué criterio se calificó a los primeros? Si el
sistema solo guarda una referencia a la rúbrica actual, sus notas quedan **indefendibles**:
el desglose por criterio dejaría de cuadrar con la nota total, o directamente mostraría
criterios que no se evaluaron.

Ante una reclamación, "tu nota se calculó con una rúbrica que ya no existe" no es una
respuesta admisible.

## Decisión

**En el momento de iniciar la sesión, se copia la rúbrica completa —criterios, pesos y
umbral— dentro de `sesion.rubrica_congelada` (JSONB).**

Toda la calificación y toda la presentación posterior de esa sesión usan la copia congelada,
nunca la rúbrica viva.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Referencia a la rúbrica viva | Simple, pero rompe la defendibilidad de las notas históricas: es el problema que motiva este ADR. |
| Versionado de rúbricas con tabla de versiones | Correcto y normalizado, y permite comparar versiones. Descartado por coste: exige gestionar el ciclo de vida de versiones y resolver a qué versión apunta cada sesión. El JSONB da el 90 % del beneficio con el 10 % del trabajo. |
| Prohibir editar la rúbrica una vez publicada la guía | Elimina el problema, pero es hostil: el instructor detecta un error de peso y no puede corregirlo para los siguientes. |

## Consecuencias

**Positivas**
- Toda sesión es auto-contenida y auditable: la evidencia incluye con qué vara se midió.
- El instructor puede mejorar sus rúbricas sin miedo a corromper el histórico.
- El reporte exportado es íntegro por sí solo, sin depender del estado actual de la base.

**Negativas**
- Duplicación de datos. Aceptable: la rúbrica es un documento pequeño (unos cientos de bytes).
- Dos aprendices de la misma ficha pueden haberse evaluado con rúbricas distintas.
  **Esto es información valiosa, no un defecto** — la interfaz de revisión lo indica
  explícitamente al instructor.
- Cambiar el formato de la rúbrica en el futuro exige contemplar los JSONB antiguos.
  Mitigación: se guarda un campo `version_esquema` dentro del JSONB.

## Precedente

Es el mismo patrón que aplica una factura al congelar el precio y los datos fiscales del
momento de la emisión, en lugar de referenciar el catálogo vivo.
