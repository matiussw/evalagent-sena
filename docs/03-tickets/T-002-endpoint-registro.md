# T-002 · Endpoint de registro de instructor

| Campo | Valor |
|---|---|
| **Tipo** | Característica |
| **Historia** | [HU-01](../02-backlog/02-historias-usuario.md#hu-01--registro-de-instructor) |
| **Épica** | E1 · Identidad y multi-tenancy |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 3 pts |
| **Componente** | `backend/app/api/v1/auth.py` |
| **Estado** | `Por hacer` |

## Descripción

Exponer `POST /api/v1/auth/registro` para que un instructor cree su cuenta indicando su
institución. La contraseña se almacena con bcrypt (coste ≥ 12) y la respuesta ya devuelve
el par de tokens, de modo que el registro deja al usuario dentro de la aplicación.

## Alcance técnico

- Esquema `RegistroRequest`: `nombre`, `email` (`EmailStr`), `password` (min. 8),
  `institucion_id`.
- Esquema `TokenResponse`: `access_token`, `refresh_token`, `token_type`, `usuario`.
- Hash con `passlib[bcrypt]`, `rounds=12`.
- Rol asignado por el servidor: siempre `DOCENTE`. **El cliente no puede elegir rol.**
- `409` si el email ya existe · `422` si la contraseña es corta o la institución no existe.

## Criterios de aceptación

- [ ] Registro válido devuelve `201` con tokens y los datos del usuario **sin** el hash.
- [ ] Email duplicado devuelve `409` con mensaje "El correo ya está registrado".
- [ ] Contraseña de menos de 8 caracteres devuelve `422`.
- [ ] Enviar `"rol": "ADMIN"` en el cuerpo **no** escala privilegios: el usuario sale `DOCENTE`.
- [ ] La contraseña en claro no aparece en ningún log.

## Definición de terminado

Endpoint documentado en OpenAPI · 5 tests de integración en verde · revisión de seguridad del hash.

## Dependencias

**Requiere:** T-001. **Bloquea:** T-003.
