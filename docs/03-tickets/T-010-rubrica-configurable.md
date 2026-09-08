# T-010 · Rúbrica configurable por guía

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-11](../02-backlog/02-historias-usuario.md#hu-11--definir-la-rúbrica-de-una-guía) |
| **Épica** | E4 · Evaluación y rúbricas |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/v1/rubricas.py` |
| **Estado** | `Por hacer` |

## Descripción

Sustituir el diccionario `SCORING_CRITERIA` hardcodeado (deuda **D8**) por rúbricas que
define el instructor. Es la pieza que resuelve el problema **P2**: el criterio deja de
depender de quién o cuándo evalúa, y pasa a estar escrito y ser el mismo para toda la ficha.

## Alcance técnico

- Modelo `Rubrica`: `guia_id` (1:1), `umbral_aprobacion` (por defecto 60).
- Modelo `CriterioRubrica`: `rubrica_id`, `nombre`, `descripcion`, `peso`, `orden`.
- Validación a nivel de servicio: los pesos deben sumar exactamente 100.
- Endpoints: `PUT /api/v1/guias/{id}/rubrica` (reemplazo completo), `GET`.
- Plantillas de arranque: "API REST" y "Fundamentos de Python" (las de la v1), ofrecidas
  como punto de partida editable.
- Cálculo: `nota = Σ(puntuacion_criterio / 10 × peso)`; aprobado si `nota ≥ umbral`.

## Criterios de aceptación

- [ ] Pesos que suman 90 o 110 devuelven `422` con el detalle del error.
- [ ] Una rúbrica con 5 criterios produce 5 puntuaciones en el reporte.
- [ ] Caso aritmético: criterios al 40/30/30 con puntuaciones 8/6/10 → nota 80 %.
- [ ] Umbral 70 con nota 68 → `aprobado = false`.
- [ ] Modificar la rúbrica **no** altera las notas de sesiones ya calificadas.
- [ ] Aplicar una plantilla precarga sus criterios y sigue siendo editable.

## Definición de terminado

Tests del cálculo ponderado · inmutabilidad de sesiones históricas verificada · plantillas cargadas por seed.

## Dependencias

**Requiere:** T-006. **Bloquea:** T-009, T-011.

## Nota de diseño

Las sesiones calificadas guardan una **copia congelada** de la rúbrica aplicada. Si el
instructor la cambia a mitad de trimestre, las notas ya emitidas siguen siendo defendibles.
