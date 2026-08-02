# T-003 · Autenticación JWT con access y refresh

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-02](../02-backlog/02-historias-usuario.md#hu-02--inicio-de-sesión-con-rol) |
| **Épica** | E1 · Identidad y multi-tenancy |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/core/security.py` · `backend/app/api/v1/auth.py` |
| **Estado** | `Por hacer` |

## Descripción

Implementar el ciclo completo de sesión: login, emisión de tokens, dependencia de FastAPI
que resuelve el usuario actual, y renovación mediante refresh token. El *claim* de
institución viaja dentro del token porque es la pieza sobre la que se apoya el aislamiento
multi-tenant (T-004).

## Alcance técnico

- `POST /api/v1/auth/login` (form OAuth2) → `access` (30 min) + `refresh` (7 días).
- `POST /api/v1/auth/refresh` → nuevo par de tokens.
- `GET /api/v1/auth/yo` → datos del usuario autenticado.
- Payload del JWT: `sub` (id usuario), `rol`, `tid` (id institución), `exp`, `type`.
- `get_usuario_actual()` como dependencia reutilizable.
- `requiere_rol(*roles)` como factoría de dependencias para autorización.
- Rate limiting: 5 intentos por IP y minuto en `/login`.
- Firma HS256 con `SECRET_KEY` leída de variable de entorno.

## Criterios de aceptación

- [ ] Credenciales válidas devuelven `200` con ambos tokens.
- [ ] Credenciales inválidas devuelven `401` con mensaje genérico que **no** revela si el email existe.
- [ ] Token caducado en endpoint protegido devuelve `401`.
- [ ] Un token de tipo `refresh` **no** sirve para autenticar peticiones normales.
- [ ] `requiere_rol("DOCENTE")` devuelve `403` a un `APRENDIZ`.
- [ ] Al sexto intento fallido en un minuto se devuelve `429`.
- [ ] El arranque falla explícitamente si `SECRET_KEY` no está definida.

## Definición de terminado

7 tests de integración en verde · rate limiting verificado · `.env.example` actualizado.

## Dependencias

**Requiere:** T-001, T-002. **Bloquea:** T-004 y todo endpoint protegido.
