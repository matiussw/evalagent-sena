# T-004 · Aislamiento multi-tenant por institución

| Campo | Valor |
|---|---|
| **Tipo** | Tarea técnica (seguridad) |
| **Historia** | [HU-03](../02-backlog/02-historias-usuario.md#hu-03--aislamiento-entre-instituciones) |
| **Épica** | E1 · Identidad y multi-tenancy |
| **Prioridad** | 🔴 Crítica |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/api/deps.py` · `backend/app/repositories` |
| **Estado** | `Por hacer` |

## Descripción

Garantizar que ningún usuario pueda leer ni modificar datos de otra institución. Es un
requisito legal (Ley 1581/2012), no una mejora. La regla de oro: **el tenant se deriva
siempre del token JWT, nunca de un parámetro que envíe el cliente**.

## Alcance técnico

- Dependencia `institucion_actual()` que extrae `tid` del token.
- Clase base `RepositorioTenant` cuyo `get`, `listar` y `actualizar` inyectan
  `WHERE institucion_id = :tid` de forma obligatoria.
- Los esquemas Pydantic de entrada **no exponen** `institucion_id`: se asigna en el servicio.
- Acceso cruzado responde `404`, no `403`, para no confirmar la existencia del recurso.
- Test parametrizado que recorre **todos** los endpoints de dominio con un usuario de otra
  institución y exige `404` en todos.

## Criterios de aceptación

- [ ] `GET /api/v1/fichas/{id}` de otra institución devuelve `404`.
- [ ] `GET /api/v1/fichas` devuelve exclusivamente fichas del tenant del token.
- [ ] Enviar `institucion_id` ajeno en el cuerpo de un `POST` se ignora: el recurso se crea en el tenant del token.
- [ ] El test parametrizado cubre el 100 % de los endpoints de dominio.
- [ ] Un intento de acceso cruzado queda registrado en el log de auditoría.

## Definición de terminado

Test parametrizado en verde sobre todos los endpoints · revisión de seguridad · KPI **K8 = 0**.

## Dependencias

**Requiere:** T-003. **Bloquea:** T-005, T-006, T-007.

## Notas

Se descarta un esquema de Postgres por tenant: multiplica la complejidad de las migraciones
para el volumen esperado. Ver [ADR-003](../04-arquitectura/adr/ADR-003-multitenancy.md).
