# Proyecto: API REST de Gestión de Tareas

## Tecnologías utilizadas
- **Runtime**: Node.js v20
- **Framework**: Express.js 4.18
- **Base de datos**: MongoDB con Mongoose
- **Autenticación**: JWT (JSON Web Tokens)
- **Despliegue**: Local en puerto 3000

## Endpoints implementados

### Autenticación
- `POST /api/auth/register` — Registro de usuario (nombre, email, password)
- `POST /api/auth/login` — Login, retorna JWT token

### Tareas (requieren JWT en header Authorization)
- `GET /api/tasks` — Listar todas las tareas del usuario autenticado
- `POST /api/tasks` — Crear nueva tarea (título, descripción, prioridad)
- `PUT /api/tasks/:id` — Actualizar tarea por ID
- `DELETE /api/tasks/:id` — Eliminar tarea por ID
- `PATCH /api/tasks/:id/complete` — Marcar tarea como completada

## Modelo de datos

```
Usuario: { nombre, email, password (hash bcrypt), createdAt }
Tarea: { título, descripción, prioridad (alta/media/baja), completada, userId, createdAt }
```

## Manejo de errores
- 400: Datos inválidos o faltantes
- 401: Token inválido o expirado
- 404: Recurso no encontrado
- 500: Error interno del servidor

## Decisiones de diseño
- Se usó MongoDB porque los datos de tareas son flexibles y no relacionales
- JWT stateless para no necesitar sesiones en servidor
- bcrypt para hash de contraseñas (salt rounds: 10)
- Variables de entorno con dotenv para credenciales

## Dificultades encontradas
- El middleware de autenticación inicialmente no pasaba el userId al siguiente middleware
- Las queries de MongoDB no filtraban por usuario, mostraba tareas de todos
