# 01 — Especificación de la API

> Base: `/api/v1` · Autenticación: `Authorization: Bearer <access_token>`
> Documentación interactiva generada por FastAPI en `/docs` (OpenAPI 3.1)

---

## 1. Convenciones

| Aspecto | Convención |
|---|---|
| **Versionado** | Prefijo de ruta `/api/v1`. Un cambio incompatible abre `/api/v2`. |
| **Identificadores** | UUID v4 en todos los recursos. |
| **Fechas** | ISO 8601 con zona horaria (`2026-09-10T14:30:00-05:00`). |
| **Paginación** | `?pagina=1&tamano=20`; la respuesta incluye `total`, `pagina`, `tamano`. |
| **Errores** | RFC 7807 (`application/problem+json`). |
| **Tenant** | Se toma del *claim* `tid` del JWT. **Nunca se acepta por parámetro ni por cuerpo.** |
| **Recurso ajeno** | `404`, no `403` — no se confirma la existencia de recursos de otro tenant. |

### Formato de error

```json
{
  "type": "https://evalagent.sena.edu.co/errores/pesos-invalidos",
  "title": "Los pesos de la rúbrica no suman 100",
  "status": 422,
  "detail": "La suma actual es 90. Ajusta los criterios para completar 100.",
  "instance": "/api/v1/guias/3f2a.../rubrica"
}
```

### Códigos de estado

| Código | Uso |
|---|---|
| `200` | Operación correcta |
| `201` | Recurso creado |
| `204` | Eliminación o acción sin cuerpo de respuesta |
| `401` | Sin token, token inválido o caducado |
| `403` | Autenticado pero sin permiso para esta acción |
| `404` | No existe **o pertenece a otro tenant** |
| `409` | Conflicto de estado (duplicado, sesión ya completada) |
| `422` | Entidad no procesable (validación de negocio) |
| `429` | Límite de peticiones superado |

---

## 2. Autenticación · `/auth`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `POST` | `/auth/registro` | público | Alta de instructor. Devuelve tokens. |
| `POST` | `/auth/login` | público | Inicio de sesión (OAuth2 password flow). |
| `POST` | `/auth/refresh` | público | Renueva el par de tokens. |
| `GET` | `/auth/yo` | autenticado | Datos del usuario actual. |

<details>
<summary><code>POST /auth/registro</code></summary>

**Petición**
```json
{
  "nombre": "Carolina Restrepo",
  "email": "carolina@sena.edu.co",
  "password": "unaClaveSegura2026",
  "institucion_id": "9c1e5a30-..."
}
```

**Respuesta `201`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "usuario": {
    "id": "4a7b...",
    "nombre": "Carolina Restrepo",
    "email": "carolina@sena.edu.co",
    "rol": "DOCENTE",
    "institucion_id": "9c1e5a30-..."
  }
}
```

**Errores:** `409` correo ya registrado · `422` contraseña corta o institución inexistente.

> El campo `rol` se ignora si llega en la petición: el servidor asigna siempre `DOCENTE`.

</details>

### Contenido del JWT

```json
{
  "sub": "4a7b...",         // id del usuario
  "rol": "DOCENTE",
  "tid": "9c1e5a30-...",    // id de institución — base del aislamiento
  "type": "access",
  "exp": 1785000000
}
```

---

## 3. Gestión académica

### Fichas · `/fichas`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `POST` | `/fichas` | DOCENTE | Crear ficha |
| `GET` | `/fichas` | DOCENTE, APRENDIZ | Listar (docente: las suyas; aprendiz: donde está inscrito) |
| `GET` | `/fichas/{id}` | DOCENTE, APRENDIZ | Detalle |
| `PATCH` | `/fichas/{id}` | DOCENTE (dueño) | Actualizar |
| `POST` | `/fichas/{id}/archivar` | DOCENTE (dueño) | Archivar |

### Inscripciones · `/fichas/{id}/inscripciones`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `POST` | `/fichas/{id}/inscripciones` | DOCENTE (dueño) | Inscribir un aprendiz por correo |
| `POST` | `/fichas/{id}/inscripciones/csv` | DOCENTE (dueño) | Carga masiva |
| `GET` | `/fichas/{id}/inscripciones` | DOCENTE (dueño) | Listar aprendices |
| `DELETE` | `/fichas/{id}/inscripciones/{ins}` | DOCENTE (dueño) | Retirar |

<details>
<summary><code>POST /fichas/{id}/inscripciones/csv</code> — respuesta</summary>

```json
{
  "creadas": 27,
  "duplicadas": 2,
  "errores": [
    { "fila": 14, "motivo": "Correo con formato inválido: jhon@@sena" }
  ]
}
```
</details>

### Guías · `/fichas/{id}/guias` y `/guias/{id}`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `POST` | `/fichas/{id}/guias` | DOCENTE (dueño) | Crear guía en `BORRADOR` |
| `GET` | `/fichas/{id}/guias` | DOCENTE, APRENDIZ | Listar (aprendiz solo ve `PUBLICADA`) |
| `GET` | `/guias/{id}` | DOCENTE, APRENDIZ | Detalle con rúbrica |
| `PATCH` | `/guias/{id}` | DOCENTE (dueño) | Actualizar |
| `POST` | `/guias/{id}/publicar` | DOCENTE (dueño) | Publicar — exige rúbrica y contexto técnico |

<details>
<summary><code>POST /fichas/{id}/guias</code></summary>

```json
{
  "titulo": "API REST de gestión de tareas",
  "descripcion": "Sustentación del proyecto de la competencia 220501096",
  "contexto_tecnico": "## Alcance\nAPI REST con Node.js, Express y MongoDB...\n\n## Temas evaluables\n- Endpoints y verbos HTTP\n- Códigos de estado y manejo de errores\n- Modelo de datos y decisiones de diseño\n- Autenticación con JWT",
  "num_preguntas": 8,
  "abre_en": "2026-09-10T08:00:00-05:00",
  "cierra_en": "2026-09-20T23:59:00-05:00"
}
```

> `contexto_tecnico` es el campo que ancla las preguntas del agente al temario real.
> Cuanto más específico, mejores preguntas.
</details>

### Rúbricas · `/guias/{id}/rubrica`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `PUT` | `/guias/{id}/rubrica` | DOCENTE (dueño) | Reemplaza la rúbrica completa |
| `GET` | `/guias/{id}/rubrica` | DOCENTE, APRENDIZ | Consultar |
| `GET` | `/rubricas/plantillas` | DOCENTE | Plantillas de arranque |

<details>
<summary><code>PUT /guias/{id}/rubrica</code></summary>

```json
{
  "umbral_aprobacion": 60,
  "criterios": [
    { "nombre": "Endpoints", "descripcion": "Comprensión de endpoints y verbos HTTP", "peso": 25 },
    { "nombre": "Manejo de errores", "descripcion": "Códigos de estado y validaciones", "peso": 20 },
    { "nombre": "Diseño", "descripcion": "Decisiones de arquitectura y tecnología", "peso": 20 },
    { "nombre": "Seguridad", "descripcion": "Autenticación y control de acceso", "peso": 15 },
    { "nombre": "Explicación", "descripcion": "Capacidad de explicar el código con sus propias palabras", "peso": 20 }
  ]
}
```

**Error `422`** si los pesos no suman exactamente 100.
</details>

---

## 4. Sustentación

### Sesiones · `/sesiones`

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `POST` | `/sesiones` | APRENDIZ | Iniciar sustentación. Devuelve el ticket del WebSocket. |
| `GET` | `/sesiones/{id}` | APRENDIZ (dueño), DOCENTE | Estado y turnos |
| `GET` | `/sesiones` | DOCENTE | Bandeja filtrable por ficha, guía y estado |
| `POST` | `/sesiones/{id}/latido` | APRENDIZ (dueño) | Mantener viva la sesión |

<details>
<summary><code>POST /sesiones</code></summary>

**Petición**
```json
{
  "guia_id": "7d3c...",
  "consentimiento_aceptado": true
}
```

**Respuesta `201`**
```json
{
  "id": "b2f9...",
  "estado": "INICIADA",
  "guia": { "titulo": "API REST de gestión de tareas", "num_preguntas": 8 },
  "rubrica_congelada": { "umbral_aprobacion": 60, "criterios": [ ... ] },
  "ws_ticket": "eyJhbGciOiJIUzI1NiIs...",
  "ws_url": "/api/v1/ws/sesiones/b2f9..."
}
```

**Errores:** `403` sin inscripción activa o fuera de ventana · `409` guía ya sustentada ·
`422` sin consentimiento.

> El `ws_ticket` caduca a los 60 segundos y es de un solo uso.
</details>

### Canal WebSocket · `WS /ws/sesiones/{id}?ticket=<jwt>`

**Mensajes del cliente al servidor**

| Tipo | Cuerpo | Descripción |
|---|---|---|
| `audio_chunk` | `{ "audio": "<base64>", "mime_type": "audio/webm" }` | Respuesta hablada del aprendiz (máx. 10 MB) |
| `latido` | `{}` | Mantiene viva la sesión |
| `finalizar` | `{}` | Cierre anticipado por el aprendiz |

**Mensajes del servidor al cliente**

| Tipo | Cuerpo | Descripción |
|---|---|---|
| `mensaje_agente` | `{ "texto", "audio", "pregunta_num", "total_preguntas", "es_final" }` | Intervención del agente |
| `transcripcion_aprendiz` | `{ "texto" }` | Lo que se entendió de la respuesta |
| `transcripcion_vacia` | `{}` | No se detectó voz — no consume pregunta |
| `estado_agente` | `{ "estado": "transcribiendo\|pensando\|hablando" }` | Estado intermedio para la interfaz |
| `evaluacion_completa` | `{ "sesion_id", "estado": "PENDIENTE_REVISION" }` | Fin. **No incluye nota alguna.** |
| `error` | `{ "codigo", "mensaje" }` | Fallo recuperable |

**Códigos de cierre**

| Código | Motivo |
|---|---|
| `4401` | Ticket ausente, inválido, caducado o ya consumido |
| `4403` | El ticket no corresponde a este aprendiz o a esta sesión |
| `4409` | La sesión no está en un estado que admita conversación |
| `1011` | Error interno (LLM caído tras agotar reintentos) |

> `evaluacion_completa` **nunca** transporta puntuaciones. Es la materialización en el
> protocolo de [ADR-006](../04-arquitectura/adr/ADR-006-humano-en-el-bucle.md).

---

## 5. Revisión y resultados

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `GET` | `/sesiones/{id}/revision` | DOCENTE (dueño de la ficha) | Transcripción + propuesta del agente |
| `POST` | `/sesiones/{id}/revision` | DOCENTE (dueño de la ficha) | Confirmar la calificación |
| `POST` | `/sesiones/{id}/reclamar` | APRENDIZ (dueño) | Abrir reclamación |
| `GET` | `/mis-resultados` | APRENDIZ | Resultados propios ya publicados |
| `GET` | `/fichas/{id}/desempeno` | DOCENTE (dueño) | Agregados por criterio |
| `GET` | `/sesiones/{id}/exportar` | DOCENTE, APRENDIZ (dueño) | Descarga en JSON o PDF |

<details>
<summary><code>POST /sesiones/{id}/revision</code></summary>

**Petición**
```json
{
  "puntuaciones_finales": {
    "Endpoints": 8,
    "Manejo de errores": 6,
    "Diseño": 7,
    "Seguridad": 5,
    "Explicación": 9
  },
  "retroalimentacion": "Explicas muy bien el flujo general y las rutas. Refuerza los códigos de estado: confundiste 401 con 403. Revisa también cómo proteges los endpoints de escritura."
}
```

**Respuesta `200`**
```json
{
  "sesion_id": "b2f9...",
  "estado": "CALIFICADA",
  "nota_final": 71.5,
  "aprobado": true,
  "revisor": { "id": "4a7b...", "nombre": "Carolina Restrepo" },
  "confirmada_en": "2026-09-12T16:04:00-05:00",
  "diferencias_con_agente": {
    "Seguridad": { "agente": 3, "final": 5 },
    "Explicación": { "agente": 7, "final": 9 }
  }
}
```

> `diferencias_con_agente` es la evidencia de supervisión humana efectiva y alimenta los
> KPIs **K4** y **K5**.
</details>

<details>
<summary><code>GET /mis-resultados</code> — sesión aún sin revisar</summary>

```json
{
  "resultados": [
    {
      "sesion_id": "b2f9...",
      "guia": "API REST de gestión de tareas",
      "estado": "PENDIENTE_REVISION",
      "mensaje": "Pendiente de revisión del instructor"
    }
  ]
}
```

> No aparece ninguna puntuación. La propuesta del agente no es visible para el aprendiz
> bajo ninguna circunstancia.
</details>

---

## 6. Operación

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `GET` | `/health` | público | Estado del servicio y de sus dependencias |

```json
{
  "status": "ok",
  "version": "2.0.0",
  "db": "ok",
  "ollama": { "estado": "ok", "modelo": "llama3.1:8b" },
  "stt": { "estado": "ok", "modelo": "medium" },
  "tts": { "estado": "ok", "motor": "piper", "voz": "es_ES-davefx-medium" },
  "sesiones_activas": 3
}
```

> El campo `tts.motor` responde al criterio de aceptación de
> [T-012](../03-tickets/T-012-tts-multiplataforma.md): permite verificar en producción qué
> motor se seleccionó realmente.

---

## 7. Matriz de autorización

| Recurso | ADMIN | DOCENTE | APRENDIZ |
|---|---|---|---|
| Instituciones | CRUD | — | — |
| Usuarios de su institución | CRUD | Leer | — |
| Fichas propias | Leer | CRUD | Leer si inscrito |
| Fichas de otro docente | Leer | — | — |
| Guías | Leer | CRUD en fichas propias | Leer si publicada e inscrito |
| Rúbricas | Leer | CRUD en fichas propias | Leer |
| Sesión propia | Leer | Leer en fichas propias | Crear y leer la suya |
| Revisión | Leer | **Confirmar en fichas propias** | — |
| Resultados | Leer | Leer en fichas propias | Leer los suyos si `CALIFICADA` |
| Auditoría | Leer | Leer en fichas propias | — |

**Regla transversal:** toda fila de esta matriz se evalúa **después** del filtro de tenant.
Un `ADMIN` de la institución A no tiene ningún acceso a la institución B.
