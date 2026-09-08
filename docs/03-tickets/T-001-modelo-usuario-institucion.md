# T-001 · Modelar Institución, Usuario y roles con SQLAlchemy

| Campo | Valor |
|---|---|
| **Tipo** | Tarea técnica |
| **Historia** | [HU-01](../02-backlog/02-historias-usuario.md#hu-01--registro-de-instructor) |
| **Épica** | E1 · Identidad y multi-tenancy |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 3 pts |
| **Componente** | `backend/app/models` · `backend/alembic` |
| **Estado** | `Por hacer` |

## Descripción

Crear la base de persistencia del sistema: la entidad `Institucion` (tenant) y la entidad
`Usuario`, con el enumerado de roles. Es el cimiento sobre el que se apoya el resto del
dominio, así que define también la clase base con las columnas comunes de auditoría
(`id`, `creado_en`, `actualizado_en`).

## Alcance técnico

- `Base` declarativa con `id: UUID` (pk), `creado_en`, `actualizado_en`.
- `Institucion`: `nombre`, `nit` (único), `activa`.
- `Usuario`: `nombre`, `email` (único global), `password_hash`, `rol`, `activo`,
  `institucion_id` (FK, `ondelete=RESTRICT`).
- Enum `RolUsuario`: `ADMIN` · `DOCENTE` · `APRENDIZ`.
- Índice compuesto `(institucion_id, rol)` para los listados filtrados por tenant.
- Migración inicial de Alembic que crea ambas tablas.

## Criterios de aceptación

- [ ] `alembic upgrade head` crea las tablas `instituciones` y `usuarios` sin errores.
- [ ] `alembic downgrade base` las elimina limpiamente.
- [ ] Insertar dos usuarios con el mismo email falla por restricción única.
- [ ] Un usuario no puede existir sin `institucion_id`.
- [ ] Borrar una institución con usuarios asociados es rechazado por la FK.
- [ ] `password_hash` nunca aparece en el `__repr__` del modelo.

## Definición de terminado

Migración aplicada · tests de modelo en verde · `docs/04-arquitectura/02-modelo-datos.md` actualizado.

## Dependencias

Ninguna. **Bloquea:** T-002, T-003, T-004, T-005.
