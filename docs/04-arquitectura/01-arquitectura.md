# 01 — Arquitectura del sistema

> EvalAgent SENA v2.0 · Modelo **C4** (Contexto → Contenedores → Componentes → Código)
> Diagramas como código en Mermaid, renderizables en GitHub, GitLab y VS Code.

---

## 1. Principios de arquitectura

| # | Principio | Consecuencia práctica |
|---|---|---|
| **A1** | **La IA corre dentro de la institución** | Whisper, Llama y Piper son procesos locales. Cero llamadas a APIs de terceros. ([ADR-001](adr/ADR-001-ejecucion-local-llm.md)) |
| **A2** | **El tenant vive en el token, no en la petición** | El cliente jamás elige de qué institución lee. ([ADR-003](adr/ADR-003-multitenancy.md)) |
| **A3** | **Ninguna nota se publica sin humano** | La arquitectura no contempla una ruta automática a `CALIFICADA`. ([ADR-006](adr/ADR-006-humano-en-el-bucle.md)) |
| **A4** | **El estado de la sesión es persistente** | Un reinicio del servidor no destruye una sustentación en curso. Corrige la deuda D7. |
| **A5** | **La voz es sustituible** | El TTS es una interfaz con varias implementaciones; nunca una llamada directa a un binario del sistema. ([ADR-005](adr/ADR-005-tts-multiplataforma.md)) |
| **A6** | **Solo texto se persiste** | El audio se procesa en memoria y se descarta. Minimización de datos por diseño. |

---

## 2. Nivel 1 — Contexto del sistema

```mermaid
C4Context
    title Nivel 1 · Contexto — EvalAgent SENA

    Person(aprendiz, "Aprendiz ADSO", "Sustenta oralmente su guía de aprendizaje")
    Person(instructor, "Instructor", "Publica guías y rúbricas, revisa y confirma notas")
    Person(coordinacion, "Coordinación académica", "Consulta evidencias y desempeño por ficha")
    Person(admin, "Administrador", "Da de alta instituciones y usuarios")

    System(evalagent, "EvalAgent SENA", "Plataforma SaaS de sustentación oral asistida por IA")

    System_Ext(navegador, "Navegador web", "Captura de micrófono y reproducción de audio")
    System_Ext(sofia, "Sofía Plus / Territorium", "Sistemas académicos del SENA (integración futura)")

    Rel(aprendiz, evalagent, "Sustenta por voz", "HTTPS / WSS")
    Rel(instructor, evalagent, "Gestiona y califica", "HTTPS")
    Rel(coordinacion, evalagent, "Consulta reportes", "HTTPS")
    Rel(admin, evalagent, "Administra", "HTTPS")
    Rel(evalagent, navegador, "Sirve la SPA", "HTTPS")
    Rel_Back(sofia, evalagent, "Exportación de notas (post-MVP)", "CSV")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

> **Frontera clave:** no hay ninguna flecha hacia un proveedor externo de IA. Es el
> requisito **R1** del análisis de la problemática y la ventaja competitiva del Lean Canvas.

---

## 3. Nivel 2 — Contenedores

```mermaid
C4Container
    title Nivel 2 · Contenedores — EvalAgent SENA

    Person(aprendiz, "Aprendiz")
    Person(instructor, "Instructor")

    System_Boundary(sistema, "EvalAgent SENA · infraestructura del centro") {
        Container(spa, "Web SPA", "React 18 + Vite + TypeScript", "Login, gestión académica y sala de sustentación")
        Container(api, "API", "Python 3.11 + FastAPI", "REST + WebSocket, autenticación, autorización multi-tenant")
        ContainerDb(db, "Base de datos", "PostgreSQL 16", "Dominio completo: usuarios, fichas, guías, sesiones, revisiones")
        Container(ollama, "Servicio LLM", "Ollama + Llama 3.1 8B", "Razonamiento del agente y propuesta de calificación")
        Container(whisper, "Servicio STT", "faster-whisper medium", "Transcripción de voz a texto en español")
        Container(piper, "Servicio TTS", "Piper es_ES-davefx-medium", "Síntesis de voz del agente")
    }

    Rel(aprendiz, spa, "Usa", "HTTPS")
    Rel(instructor, spa, "Usa", "HTTPS")
    Rel(spa, api, "REST", "JSON/HTTPS")
    Rel(spa, api, "Sesión de voz", "WSS")
    Rel(api, db, "Lee y escribe", "SQLAlchemy async")
    Rel(api, ollama, "Genera preguntas y califica", "HTTP local :11434")
    Rel(api, whisper, "Transcribe audio", "En proceso")
    Rel(api, piper, "Sintetiza voz", "Subproceso")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Comparativa v1 → v2

| Aspecto | v1 | v2 |
|---|---|---|
| Frontend | 2 ficheros HTML sueltos | SPA React con rutas y roles |
| Autenticación | ninguna | JWT con roles y multi-tenancy |
| Persistencia | ficheros `.md` y `.json` | PostgreSQL con migraciones |
| Estado de sesión | `dict` en memoria | tabla `sesion` |
| Criterios de evaluación | hardcodeados (`python`/`api`) | rúbrica por guía definida por el instructor |
| Calificación | propuesta = nota final | propuesta → revisión humana → nota |
| TTS | `say` de macOS | Piper (Linux, macOS, Windows) |
| Despliegue | `start.sh` local | Docker Compose + CI/CD |

---

## 4. Nivel 3 — Componentes de la API

```mermaid
C4Component
    title Nivel 3 · Componentes — Contenedor API

    Container_Boundary(api, "API · FastAPI") {
        Component(rt_auth, "Router de autenticación", "APIRouter", "registro, login, refresh, yo")
        Component(rt_acad, "Router académico", "APIRouter", "fichas, inscripciones, guías, rúbricas")
        Component(rt_ses, "Router de sesiones", "APIRouter", "crear sesión, consultar, revisar")
        Component(rt_ws, "Router WebSocket", "APIRouter", "canal de voz en tiempo real")

        Component(deps, "Dependencias de seguridad", "deps.py", "usuario_actual, requiere_rol, institucion_actual")
        Component(sec, "Núcleo de seguridad", "security.py", "bcrypt, emisión y validación de JWT")

        Component(svc_acad, "Servicio académico", "Servicio", "Reglas de fichas, guías y rúbricas")
        Component(svc_ses, "Servicio de sesión", "Servicio", "Máquina de estados de la sustentación")
        Component(svc_agente, "Motor del agente", "Servicio", "Orquesta la conversación y la calificación")
        Component(svc_rev, "Servicio de revisión", "Servicio", "Confirmación humana y auditoría")

        Component(ad_stt, "Adaptador STT", "Adaptador", "faster-whisper")
        Component(ad_tts, "Adaptador TTS", "Adaptador", "Piper / say / espeak")
        Component(ad_llm, "Adaptador LLM", "Adaptador", "Cliente de Ollama")

        Component(repos, "Repositorios", "SQLAlchemy", "Acceso a datos con filtro de tenant obligatorio")
    }

    ContainerDb(db, "PostgreSQL")
    Container(ollama, "Ollama")

    Rel(rt_auth, sec, "usa")
    Rel(rt_acad, deps, "protege con")
    Rel(rt_ses, deps, "protege con")
    Rel(rt_ws, deps, "valida ticket con")
    Rel(rt_acad, svc_acad, "delega en")
    Rel(rt_ses, svc_ses, "delega en")
    Rel(rt_ses, svc_rev, "delega en")
    Rel(rt_ws, svc_agente, "delega en")
    Rel(svc_agente, ad_stt, "transcribe")
    Rel(svc_agente, ad_tts, "sintetiza")
    Rel(svc_agente, ad_llm, "razona")
    Rel(ad_llm, ollama, "HTTP")
    Rel(svc_acad, repos, "usa")
    Rel(svc_ses, repos, "usa")
    Rel(svc_rev, repos, "usa")
    Rel(repos, db, "SQL")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="1")
```

### Estructura de carpetas

```
backend/
├── app/
│   ├── main.py                 # Ensamblado de la aplicación y middleware
│   ├── core/
│   │   ├── config.py           # Configuración por variables de entorno
│   │   ├── security.py         # bcrypt + JWT
│   │   └── logging.py          # Logs estructurados
│   ├── db/
│   │   ├── base.py             # Clase declarativa base
│   │   └── session.py          # Motor y sesión async
│   ├── models/                 # Entidades SQLAlchemy
│   ├── schemas/                # Contratos Pydantic (entrada/salida)
│   ├── repositories/           # Acceso a datos con filtro de tenant
│   ├── services/               # Reglas de negocio
│   │   ├── agente.py           # Motor conversacional
│   │   ├── stt.py · tts.py     # Adaptadores de voz
│   │   └── llm.py              # Cliente de Ollama
│   ├── api/
│   │   ├── deps.py             # Dependencias transversales
│   │   └── v1/                 # Routers versionados
│   └── tests/
├── alembic/                    # Migraciones
└── pyproject.toml
```

---

## 5. Nivel 4 — Flujo de un turno de conversación

```mermaid
sequenceDiagram
    autonumber
    participant A as Aprendiz
    participant SPA as Web SPA
    participant WS as Router WebSocket
    participant SES as Servicio de sesión
    participant STT as Adaptador STT
    participant AG as Motor del agente
    participant LLM as Ollama
    participant TTS as Adaptador TTS
    participant DB as PostgreSQL

    A->>SPA: habla y suelta el botón
    SPA->>WS: audio_chunk (base64)
    WS->>WS: valida ticket y tamaño (≤10 MB)
    WS->>STT: transcribir(audio)
    Note over STT: en thread pool,<br/>no bloquea el bucle de eventos
    STT-->>WS: texto
    WS->>WS: descarta el audio de memoria

    alt texto vacío
        WS-->>SPA: transcripcion_vacia
        Note over SPA: no consume pregunta
    else texto con contenido
        WS->>DB: guarda TurnoConversacion (APRENDIZ)
        WS-->>SPA: transcripcion_aprendiz
        WS->>AG: responder(texto)
        AG->>AG: arma prompt con guía + rúbrica + historial
        AG->>LLM: chat
        LLM-->>AG: siguiente pregunta
        AG->>TTS: sintetizar(texto)
        TTS-->>AG: WAV base64
        AG->>DB: guarda TurnoConversacion (AGENTE) + latencia
        AG-->>WS: texto + audio
        WS-->>SPA: mensaje_agente
        SPA->>A: reproduce audio y muestra texto
    end

    opt última pregunta
        AG->>LLM: calificar contra rúbrica congelada
        LLM-->>AG: puntuaciones por criterio
        AG->>DB: sesion.estado = PENDIENTE_REVISION
        Note over DB: NO se calcula nota publicable.<br/>Espera confirmación humana
        WS-->>SPA: evaluacion_completa
    end
```

---

## 6. Flujo de la revisión humana

```mermaid
sequenceDiagram
    autonumber
    participant I as Instructor
    participant SPA as Web SPA
    participant API as Router de sesiones
    participant REV as Servicio de revisión
    participant DB as PostgreSQL
    participant AP as Aprendiz

    I->>SPA: abre la bandeja de revisión
    SPA->>API: GET /sesiones?estado=PENDIENTE_REVISION
    API->>DB: consulta filtrada por tenant y ficha propia
    DB-->>SPA: listado

    I->>SPA: abre una sesión
    SPA->>API: GET /sesiones/{id}/revision
    API-->>SPA: transcripción + puntuaciones propuestas + rúbrica congelada

    I->>SPA: ajusta puntuaciones y escribe retroalimentación
    SPA->>API: POST /sesiones/{id}/revision
    API->>REV: confirmar(...)
    REV->>REV: verifica que es el instructor dueño de la ficha
    REV->>DB: inserta Revision + calcula nota ponderada
    REV->>DB: sesion.estado = CALIFICADA
    REV->>DB: EventoAuditoria(accion="NOTA_CONFIRMADA", detalle=diferencias)
    REV-->>SPA: 200

    AP->>SPA: consulta sus resultados
    SPA->>API: GET /mis-resultados
    API->>DB: solo sesiones CALIFICADAS
    DB-->>AP: nota, desglose por criterio y retroalimentación
```

---

## 7. Nivel de despliegue

```mermaid
flowchart TB
    subgraph internet["Internet"]
        USR["Navegadores<br/>aprendices e instructores"]
    end

    subgraph borde["Borde"]
        PROXY["Reverse proxy<br/>Caddy / Nginx<br/>TLS + WSS"]
    end

    subgraph centro["Infraestructura del centro de formación"]
        subgraph compose["Docker Compose"]
            WEB["contenedor web<br/>Nginx + build de la SPA"]
            APIC["contenedor api<br/>Uvicorn + FastAPI<br/>Whisper + Piper embebidos"]
            PG[("contenedor db<br/>PostgreSQL 16<br/>volumen persistente")]
        end
        OLL["Ollama<br/>proceso del host<br/>Llama 3.1 8B"]
    end

    USR -->|HTTPS 443| PROXY
    PROXY -->|HTTP| WEB
    PROXY -->|HTTP + WS| APIC
    APIC -->|TCP 5432| PG
    APIC -->|HTTP 11434| OLL

    style OLL fill:#f59e0b,color:#000
    style PG fill:#2563eb,color:#fff
```

**Por qué Ollama vive en el host y no en un contenedor:** el acceso a GPU desde contenedor
añade complejidad (drivers, `nvidia-container-toolkit`) que un técnico de centro de
formación no tiene por qué resolver. Ollama en el host es un instalador de un clic.

### Requisitos mínimos

| Perfil | CPU | RAM | Modelos | Sesiones simultáneas |
|---|---|---|---|---|
| **Mínimo** | 8 núcleos | 16 GB | Whisper `small` + Llama 3.2 3B | 2–3 |
| **Recomendado** | 12 núcleos | 32 GB | Whisper `medium` + Llama 3.1 8B | 8–10 |
| **Con GPU** | 8 núcleos + 8 GB VRAM | 32 GB | Whisper `medium` + Llama 3.1 8B | 15+ |

> Mitigación del riesgo **RG-4**: el perfil mínimo se activa con variables de entorno,
> sin tocar código.

---

## 8. Decisiones de arquitectura (ADRs)

| ADR | Decisión | Estado |
|---|---|---|
| [ADR-001](adr/ADR-001-ejecucion-local-llm.md) | IA 100 % local, sin APIs externas | Aceptada |
| [ADR-002](adr/ADR-002-postgres-sobre-ficheros.md) | PostgreSQL en lugar de ficheros | Aceptada |
| [ADR-003](adr/ADR-003-multitenancy.md) | Multi-tenancy por columna discriminadora | Aceptada |
| [ADR-004](adr/ADR-004-websocket-vs-webrtc.md) | WebSocket con audio por turnos, no WebRTC continuo | Aceptada |
| [ADR-005](adr/ADR-005-tts-multiplataforma.md) | TTS como interfaz con motores intercambiables | Aceptada |
| [ADR-006](adr/ADR-006-humano-en-el-bucle.md) | Confirmación humana obligatoria de toda nota | Aceptada |
| [ADR-007](adr/ADR-007-rubrica-congelada.md) | La sesión congela una copia de su rúbrica | Aceptada |

---

## 9. Atributos de calidad

| Atributo | Táctica arquitectónica |
|---|---|
| **Privacidad** | Todo el procesamiento de IA dentro del perímetro del centro; el audio nunca se persiste |
| **Seguridad** | JWT con tenant embebido; filtro obligatorio en el repositorio base; ticket de un solo uso para el WebSocket |
| **Disponibilidad** | Estado de sesión persistido: un reinicio no destruye una sustentación en curso |
| **Rendimiento** | STT en *thread pool*; audio como turnos discretos, no flujo continuo |
| **Portabilidad** | TTS como interfaz; todo el sistema en contenedores |
| **Auditabilidad** | Tabla de eventos append-only; rúbrica y propuesta del agente congeladas |
| **Evolutividad** | API versionada (`/api/v1`); servicios desacoplados de los routers |
