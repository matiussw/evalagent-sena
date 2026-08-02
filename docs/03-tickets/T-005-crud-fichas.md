# T-005 · CRUD de fichas

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-05](../02-backlog/02-historias-usuario.md#hu-05--crear-y-gestionar-fichas) |
| **Épica** | E2 · Gestión académica |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/v1/fichas.py` |
| **Estado** | `Por hacer` |

## Descripción

La ficha es la unidad organizativa del SENA: equivale a una clase de Google Classroom.
Agrupa aprendices y guías, y pertenece a un instructor dentro de una institución.

## Alcance técnico

- Modelo `Ficha`: `codigo`, `nombre`, `programa`, `trimestre`, `estado`
  (`ACTIVA` · `ARCHIVADA`), `docente_id`, `institucion_id`.
- Restricción única compuesta `(institucion_id, codigo)`.
- Endpoints: `POST`, `GET` (listado paginado), `GET /{id}`, `PATCH /{id}`,
  `POST /{id}/archivar`.
- Solo rol `DOCENTE` crea fichas; solo su dueño las modifica.
- El listado del aprendiz devuelve únicamente las fichas donde está inscrito.

## Criterios de aceptación

- [ ] Crear ficha la asocia al instructor autenticado y a su institución.
- [ ] Código duplicado dentro de la misma institución devuelve `409`.
- [ ] El mismo código en **otra** institución sí se permite.
- [ ] Archivar una ficha la saca del listado activo pero conserva sus sesiones consultables.
- [ ] Un `APRENDIZ` que llama a `POST /api/v1/fichas` recibe `403`.
- [ ] Un instructor no puede modificar la ficha de otro instructor (`404`).

## Definición de terminado

CRUD documentado en OpenAPI · 6 tests de integración · aislamiento verificado por T-004.

## Dependencias

**Requiere:** T-004. **Bloquea:** T-006, T-006.
