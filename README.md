# EvalAgent SENA 🎙️

### Plataforma de sustentación oral asistida por IA para el programa ADSO

Los instructores del SENA no pueden sustentar oralmente a 100+ aprendices por trimestre.
Cuando lo hacen, el criterio no es uniforme y no queda evidencia auditable.

**EvalAgent** es una plataforma SaaS —tipo Google Classroom— donde el instructor publica
guías de aprendizaje con su rúbrica, y sus aprendices las **sustentan hablando** con un
agente de IA. El agente pregunta, escucha, repregunta según lo que el aprendiz responde, y
entrega una transcripción íntegra con una propuesta de calificación.

**La nota final siempre la confirma el instructor.** El sistema no califica solo.

Todo el procesamiento de IA ocurre **dentro del centro de formación**: ni un dato personal
de aprendices sale hacia servicios externos.

---

## Estado del proyecto

| Componente | Estado |
|---|---|
| Documentación (PRD, backlog, arquitectura, ADRs) | ✅ Completa |
| Backend: dominio, auth multi-tenant, API REST + WebSocket | ✅ Funcional |
| Frontend React: login, panel docente, sala de sustentación, revisión | ✅ Funcional |
| Tests | ✅ 119 backend · 4 frontend |
| CI (GitHub Actions) | ✅ Configurado |
| Despliegue público | ⏳ Pendiente |

> La documentación de la v1 (monousuario, sin autenticación, persistencia en ficheros) se
> conserva en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md) como referencia
> histórica. El código de su interfaz está en `frontend/legacy/`.

---

## Arranque rápido

```bash
git clone <este-repositorio> && cd _ProyectoFinal_L1DR

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # pega el valor en SECRET_KEY

# Ollama corre en el host, no en un contenedor (ver ADR-001)
ollama pull llama3.1:8b

docker compose up
```

- Interfaz: <http://localhost:5173>
- API y documentación interactiva: <http://localhost:8000/docs>
- Estado del sistema: <http://localhost:8000/api/v1/health>

### Desarrollo sin Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

---

## Cómo se usa

### Instructor

1. Crea una **ficha** con su código, programa y trimestre.
2. Publica una **guía** con su *contexto técnico* — es lo que ancla las preguntas del agente
   al temario real. Cuanto más concreto, mejores preguntas.
3. Define la **rúbrica**: tus criterios, con sus pesos (deben sumar 100) y el umbral de
   aprobación.
4. **Inscribe** a tus aprendices por correo. Si no tienen cuenta, se crea sola.
5. Cuando terminen, entra en **Por revisar**: verás la transcripción íntegra y la propuesta
   del agente. Ajusta lo que no compartas, escribe la retroalimentación y confirma.

### Aprendiz

1. Entra en **Mis guías** y abre la que vas a sustentar.
2. Verás la rúbrica y el aviso de tratamiento de datos **antes** de empezar.
3. Mantén pulsado el botón para hablar, suéltalo al terminar. El agente repreguntará.
4. Al acabar, tu instructor revisa. La nota aparece en **Mis resultados** cuando la confirme.

---

## Arquitectura

```
Navegador ── HTTPS/WSS ──> API (FastAPI) ──> PostgreSQL
                              │
                              ├──> Whisper   (voz → texto)
                              ├──> Ollama    (razonamiento del agente)
                              └──> Piper     (texto → voz)
                              todo dentro del centro de formación
```

| Capa | Tecnología |
|---|---|
| Frontend | React 18 · Vite · TypeScript · TanStack Query |
| Backend | Python 3.11 · FastAPI · WebSocket |
| Base de datos | PostgreSQL 16 · SQLAlchemy 2.0 async · Alembic |
| Autenticación | JWT (HS256) · bcrypt · multi-tenant por institución |
| Voz a texto | faster-whisper (`medium`, es) |
| Razonamiento | Ollama · Llama 3.1 8B |
| Texto a voz | Piper (`es_ES-davefx-medium`), con reserva a `say` y espeak-ng |
| Infraestructura | Docker Compose · GitHub Actions |

Detalle completo en [`docs/04-arquitectura/`](docs/04-arquitectura/01-arquitectura.md).

### Cuatro decisiones que explican el resto

| Decisión | Por qué |
|---|---|
| [IA 100 % local](docs/04-arquitectura/adr/ADR-001-ejecucion-local-llm.md) | Trata voz de menores. Enviarla a un proveedor extranjero exigiría una transferencia internacional de datos que no procede. Además, coste marginal cero. |
| [Confirmación humana obligatoria](docs/04-arquitectura/adr/ADR-006-humano-en-el-bucle.md) | Una nota tiene efectos significativos sobre una persona. Ninguna sesión llega a `CALIFICADA` sin que un instructor la confirme — verificado por un test que inspecciona el código fuente. |
| [Rúbrica congelada por sesión](docs/04-arquitectura/adr/ADR-007-rubrica-congelada.md) | Si el instructor edita la rúbrica a mitad de trimestre, las notas ya emitidas siguen cuadrando y siendo defendibles. |
| [TTS como interfaz](docs/04-arquitectura/adr/ADR-005-tts-multiplataforma.md) | La v1 llamaba al comando `say` de macOS desde la lógica de negocio y era muda en Linux. Ahora el motor es intercambiable. |

---

## Configuración

Todo por variables de entorno. Ver [`.env.example`](.env.example) para la lista completa.

| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Firma de los JWT. **Obligatoria**, mínimo 32 caracteres. El arranque falla sin ella. |
| `DATABASE_URL` | Conexión a PostgreSQL |
| `CORS_ORIGINS` | Lista blanca separada por comas. **No admite `*`**: la API envía credenciales. |
| `OLLAMA_MODEL` | Modelo del agente (`llama3.1:8b` por defecto) |
| `WHISPER_MODEL` | `tiny` … `large`. Usa `small` en hardware limitado. |
| `TTS_ENGINE` | `auto` (recomendado), `piper`, `say`, `espeak` o `ninguno` |

### Hardware

| Perfil | CPU | RAM | Modelos | Sesiones simultáneas |
|---|---|---|---|---|
| Mínimo | 8 núcleos | 16 GB | Whisper `small` + Llama 3.2 3B | 2–3 |
| Recomendado | 12 núcleos | 32 GB | Whisper `medium` + Llama 3.1 8B | 8–10 |
| Con GPU | 8 núcleos + 8 GB VRAM | 32 GB | Whisper `medium` + Llama 3.1 8B | 15+ |

---

## Tests

```bash
cd backend && pytest --cov=app        # 119 tests
cd frontend && npm test               # 4 tests
```

Los dos más importantes:

- **`test_aislamiento_multitenant.py`** — parametrizado sobre *todos* los endpoints de
  dominio, con el rol correcto en cada uno. Incluye un guardia que falla si alguien añade
  un endpoint nuevo y olvida cubrirlo.
- **`test_humano_en_el_bucle.py`** — verifica por inspección del AST que la única asignación
  de `EstadoSesion.CALIFICADA` en todo `app/` está dentro de `ServicioRevision.confirmar`.
  Un test funcional probaría los caminos conocidos; este prueba la ausencia de otros.

---

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/`](docs/README.md) | Índice general con la trazabilidad problema → épica → historia → ticket → test |
| [`docs/01-producto/01-problematica.md`](docs/01-producto/01-problematica.md) | El problema, los dolores por rol y qué queda fuera de alcance |
| [`docs/01-producto/02-prd.md`](docs/01-producto/02-prd.md) | PRD completo con KPIs, riesgos y fases |
| [`docs/02-backlog/`](docs/02-backlog/02-historias-usuario.md) | 16 historias con Gherkin y evaluación INVEST |
| [`docs/03-tickets/`](docs/03-tickets/README.md) | 13 tickets técnicos |
| [`docs/04-arquitectura/`](docs/04-arquitectura/01-arquitectura.md) | C4, modelo de datos y 7 ADRs |
| [`docs/05-api/`](docs/05-api/01-especificacion-api.md) | Contrato REST y WebSocket |
| [`prompts.md`](prompts.md) | Prompts clave, evolución del prompt del agente y errores que cometió la IA |

---

## Privacidad

- El **audio nunca se almacena**: se procesa en memoria y se descarta. Solo persiste la
  transcripción textual.
- El aprendiz acepta un **consentimiento informado explícito** antes de su primera
  sustentación; sin él, la sesión no se crea.
- Ninguna llamada a APIs de IA de terceros. Hay un paso en CI que falla si aparece una.
- Los datos de cada institución están aislados: el identificador de tenant viaja en el token
  y jamás se acepta como parámetro del cliente.

---

*Proyecto final del Máster AI4Devs — LIDR Academy.*
