# 02 — Historias de usuario

> Formato estándar: *Como [rol], quiero [acción] para [beneficio]*
> Criterios de aceptación en **Gherkin** (Dado / Cuando / Entonces)
> Cada historia evaluada contra los criterios **INVEST**
> *(Módulo 5 — Máster AI4Devs, LIDR Academy)*

**Leyenda de estimación:** `S` ≤ 3 pts · `M` = 5 pts · `L` = 8 pts · `XL` = 13 pts

---

## Índice

| ID | Título | Épica | Prioridad | Est. |
|---|---|---|---|---|
| [HU-01](#hu-01--registro-de-instructor) | Registro de instructor | E1 | Must | M |
| [HU-02](#hu-02--inicio-de-sesión-con-rol) | Inicio de sesión con rol | E1 | Must | M |
| [HU-03](#hu-03--aislamiento-entre-instituciones) | Aislamiento entre instituciones | E1 | Must | L |
| [HU-04](#hu-04--gestión-de-instituciones-admin) | Gestión de instituciones (admin) | E1 | Could | M |
| [HU-05](#hu-05--crear-y-gestionar-fichas) | Crear y gestionar fichas | E2 | Must | M |
| [HU-06](#hu-06--inscribir-aprendices-en-una-ficha) | Inscribir aprendices en una ficha | E2 | Should | M |
| [HU-07](#hu-07--publicar-una-guía-de-aprendizaje) | Publicar una guía de aprendizaje | E2 | Must | L |
| [HU-08](#hu-08--iniciar-una-sustentación-desde-la-guía) | Iniciar una sustentación desde la guía | E3 | Must | L |
| [HU-09](#hu-09--conversar-por-voz-con-el-agente) | Conversar por voz con el agente | E3 | Must | XL |
| [HU-10](#hu-10--reanudar-una-sesión-interrumpida) | Reanudar una sesión interrumpida | E3 | Should | M |
| [HU-11](#hu-11--definir-la-rúbrica-de-una-guía) | Definir la rúbrica de una guía | E4 | Must | L |
| [HU-12](#hu-12--revisar-y-confirmar-la-calificación) | Revisar y confirmar la calificación | E4 | Must | L |
| [HU-13](#hu-13--consultar-la-retroalimentación) | Consultar la retroalimentación | E5 | Should | S |
| [HU-14](#hu-14--panel-de-desempeño-por-ficha) | Panel de desempeño por ficha | E5 | Could | M |
| [HU-15](#hu-15--levantar-el-sistema-con-un-comando) | Levantar el sistema con un comando | E6 | Must | M |
| [HU-16](#hu-16--voz-del-agente-multiplataforma) | Voz del agente multiplataforma | E6 | Must | M |

---

## E1 · Identidad y multi-tenancy

### HU-01 — Registro de instructor

> **Como** instructor del SENA
> **quiero** crear mi cuenta indicando mi institución
> **para** empezar a gestionar mis fichas sin depender de un administrador.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E1 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Registro exitoso
  Dado que no existe ninguna cuenta con el correo "carolina@sena.edu.co"
  Cuando envío el formulario con nombre, ese correo, una contraseña de 10 caracteres
    y selecciono la institución "Centro de Servicios y Gestión Empresarial"
  Entonces se crea mi cuenta con rol DOCENTE
  Y recibo un token de acceso válido
  Y mi contraseña queda almacenada como hash bcrypt, nunca en claro

Escenario: Correo ya registrado
  Dado que ya existe una cuenta con el correo "carolina@sena.edu.co"
  Cuando intento registrarme con ese mismo correo
  Entonces recibo un error 409 con el mensaje "El correo ya está registrado"
  Y no se crea ninguna cuenta nueva

Escenario: Contraseña débil
  Dado que estoy en el formulario de registro
  Cuando introduzco la contraseña "1234"
  Entonces recibo un error 422 indicando el mínimo de 8 caracteres
  Y no se crea la cuenta
```

**INVEST** — **I:** no depende de otras historias · **N:** el mecanismo (correo vs. SSO institucional) es negociable · **V:** sin cuenta no hay producto · **E:** patrón conocido · **S:** un endpoint + un formulario · **T:** los tres escenarios son automatizables.

**Tickets:** [T-001](../03-tickets/T-001-modelo-usuario-institucion.md), [T-002](../03-tickets/T-002-endpoint-registro.md)

---

### HU-02 — Inicio de sesión con rol

> **Como** usuario registrado
> **quiero** iniciar sesión y aterrizar en el panel que corresponde a mi rol
> **para** llegar directo a lo que tengo que hacer.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E1 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Login de instructor
  Dado que tengo una cuenta activa con rol DOCENTE
  Cuando inicio sesión con mis credenciales correctas
  Entonces recibo un token de acceso (30 min) y uno de refresco (7 días)
  Y la aplicación me lleva a "/docente"

Escenario: Login de aprendiz
  Dado que tengo una cuenta activa con rol APRENDIZ
  Cuando inicio sesión con mis credenciales correctas
  Entonces la aplicación me lleva a "/aprendiz"

Escenario: Credenciales incorrectas
  Dado que tengo una cuenta activa
  Cuando inicio sesión con una contraseña equivocada
  Entonces recibo un error 401 con el mensaje genérico "Credenciales inválidas"
  Y el mensaje no revela si el correo existe o no

Escenario: Protección contra fuerza bruta
  Dado que he fallado 5 intentos de login en menos de 5 minutos
  Cuando intento un sexto login
  Entonces recibo un error 429 e indicación de esperar

Escenario: Token expirado
  Dado que mi token de acceso caducó
  Cuando llamo a un endpoint protegido con ese token
  Entonces recibo un 401
  Y el frontend renueva el token con el de refresco de forma transparente
```

**INVEST** — **I:** solo requiere que exista un usuario · **N:** duración de tokens negociable · **V:** puerta de entrada · **E:** patrón JWT estándar · **S:** dos endpoints · **T:** verificable con tests de integración.

**Tickets:** [T-003](../03-tickets/T-003-jwt-login-refresh.md)

---

### HU-03 — Aislamiento entre instituciones

> **Como** responsable de protección de datos del centro
> **quiero** que ningún usuario pueda acceder a información de otra institución
> **para** cumplir la Ley 1581/2012 de protección de datos personales.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E1 | L (8) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Lectura cruzada bloqueada
  Dado que soy instructor de la institución A
  Y existe la ficha "F-99" en la institución B
  Cuando solicito GET /api/v1/fichas/F-99
  Entonces recibo un 404 (no un 403, para no revelar que el recurso existe)

Escenario: Listados filtrados
  Dado que soy instructor de la institución A
  Cuando solicito GET /api/v1/fichas
  Entonces la respuesta contiene únicamente fichas de la institución A

Escenario: El tenant no se puede falsear desde el cliente
  Dado que soy instructor de la institución A
  Cuando envío una petición con el cuerpo {"institucion_id": "B"}
  Entonces el recurso se crea igualmente en la institución A
  Porque el tenant se toma del token, nunca del cuerpo de la petición
```

**INVEST** — **I:** transversal pero implementable de una vez como dependencia de FastAPI · **N:** la estrategia (columna discriminadora vs. esquema por tenant) es negociable · **V:** requisito legal · **E:** un `Depends` + filtros en el repositorio · **S:** acotable a una capa · **T:** test dedicado por endpoint.

**Tickets:** [T-004](../03-tickets/T-004-aislamiento-multitenant.md)

---

### HU-04 — Gestión de instituciones (admin)

> **Como** administrador de la instancia
> **quiero** dar de alta instituciones y asignarles administradores
> **para** que cada centro de formación opere de forma independiente.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔵 Could-Have | E1 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Alta de institución
  Dado que tengo rol ADMIN
  Cuando creo la institución "Centro de Diseño Tecnológico Industrial" con NIT único
  Entonces la institución queda registrada y activa

Escenario: Un DOCENTE no puede crear instituciones
  Dado que tengo rol DOCENTE
  Cuando llamo a POST /api/v1/instituciones
  Entonces recibo un 403
```

**INVEST** — **I:** independiente · **N:** puede resolverse por seed en el MVP · **V:** necesaria para el modelo SaaS, no para la demo · **E:** CRUD simple · **S:** un recurso · **T:** dos escenarios.

---

## E2 · Gestión académica

### HU-05 — Crear y gestionar fichas

> **Como** instructor
> **quiero** crear fichas con su código, programa y trimestre
> **para** organizar a mis aprendices como lo hago en la realidad.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E2 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Crear ficha
  Dado que soy instructor autenticado
  Cuando creo la ficha con código "2758421", programa "ADSO" y trimestre "2026-2"
  Entonces la ficha queda asociada a mí y a mi institución
  Y aparece en mi listado de fichas

Escenario: Código de ficha duplicado en la misma institución
  Dado que ya existe la ficha "2758421" en mi institución
  Cuando intento crear otra con el mismo código
  Entonces recibo un 409

Escenario: Archivar una ficha
  Dado que tengo una ficha del trimestre anterior
  Cuando la archivo
  Entonces deja de aparecer en el listado activo
  Pero sus sesiones y reportes siguen siendo consultables
```

**INVEST** — **I:** solo depende de E1 · **N:** los campos son negociables · **V:** organiza todo el resto · **E:** CRUD · **S:** un recurso · **T:** automatizable.

**Tickets:** [T-005](../03-tickets/T-005-crud-fichas.md)

---

### HU-06 — Inscribir aprendices en una ficha

> **Como** instructor
> **quiero** inscribir a mis aprendices en una ficha
> **para** que solo ellos vean y sustenten sus guías.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🟠 Should-Have | E2 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Inscripción individual
  Dado que soy instructor de la ficha "2758421"
  Cuando inscribo el correo "jhon@aprendiz.sena.edu.co"
  Entonces se crea la inscripción en estado ACTIVA
  Y si ese correo no tenía cuenta, se crea una con rol APRENDIZ y contraseña temporal

Escenario: Carga masiva por CSV
  Dado que soy instructor de la ficha "2758421"
  Cuando subo un CSV con 30 filas de nombre y correo
  Entonces se crean 30 inscripciones
  Y recibo un resumen de creadas, duplicadas y filas con error

Escenario: El aprendiz solo ve sus fichas
  Dado que estoy inscrito únicamente en la ficha "2758421"
  Cuando consulto mis fichas
  Entonces solo aparece "2758421"
```

**INVEST** — **I:** depende de HU-05 · **N:** el CSV puede caer del MVP · **V:** sin inscripciones nadie sustenta · **E:** conocido · **S:** acotado · **T:** sí.

---

### HU-07 — Publicar una guía de aprendizaje

> **Como** instructor
> **quiero** publicar una guía con su enunciado y contexto técnico
> **para** que el agente pregunte exactamente sobre lo que enseñé.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E2 | L (8) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Publicar guía
  Dado que soy instructor de la ficha "2758421"
  Cuando creo la guía "API REST de gestión de tareas" con su contexto técnico en Markdown,
    8 preguntas, y ventana del 10 al 20 de septiembre
  Entonces la guía queda en estado PUBLICADA
  Y sus aprendices inscritos la ven en su panel

Escenario: Guía en borrador no visible
  Dado que tengo una guía en estado BORRADOR
  Cuando un aprendiz consulta sus guías
  Entonces esa guía no aparece

Escenario: Fuera de la ventana de sustentación
  Dado que la ventana de la guía cerró ayer
  Cuando un aprendiz intenta iniciar la sustentación
  Entonces recibe un 403 con el mensaje "La ventana de sustentación está cerrada"

Escenario: El contexto alimenta al agente
  Dado que la guía contiene "endpoints REST, códigos HTTP y manejo de errores"
  Cuando el agente genera preguntas
  Entonces las preguntas versan sobre esos temas y no sobre temas ajenos a la guía
```

**INVEST** — **I:** depende de HU-05 · **N:** el formato del contexto (Markdown, PDF, enlace) es negociable · **V:** es lo que ancla al agente al temario real · **E:** CRUD + un campo de texto largo · **S:** un recurso · **T:** los tres primeros escenarios son deterministas; el cuarto se verifica con una comprobación semántica.

**Tickets:** [T-006](../03-tickets/T-006-crud-guias.md)

---

## E3 · Sustentación por voz

### HU-08 — Iniciar una sustentación desde la guía

> **Como** aprendiz
> **quiero** abrir mi guía y empezar a sustentar cuando yo pueda
> **para** no depender de cuadrar agenda con el instructor.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E3 | L (8) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Inicio correcto
  Dado que estoy inscrito en la ficha y la guía está publicada y dentro de ventana
  Cuando pulso "Iniciar sustentación"
  Entonces veo la rúbrica y el número de preguntas antes de empezar
  Y tras aceptar el consentimiento informado se crea una sesión en estado INICIADA
  Y se abre el canal WebSocket

Escenario: Un solo intento por guía
  Dado que ya completé la sustentación de esta guía
  Cuando intento iniciarla de nuevo
  Entonces recibo un 409 con el mensaje "Ya sustentaste esta guía"

Escenario: Sin permiso de micrófono
  Dado que deniego el acceso al micrófono
  Cuando intento iniciar
  Entonces veo instrucciones para habilitarlo y la sesión no se crea

Escenario: Consentimiento obligatorio
  Dado que no acepto el aviso de tratamiento de datos
  Cuando intento continuar
  Entonces el botón de iniciar permanece deshabilitado
```

**INVEST** — **I:** depende de HU-07 · **N:** número de intentos negociable · **V:** elimina la barrera de agenda (P6) · **E:** conocido · **S:** un endpoint + una pantalla · **T:** sí.

**Tickets:** [T-007](../03-tickets/T-007-sesion-sustentacion.md)

---

### HU-09 — Conversar por voz con el agente

> **Como** aprendiz
> **quiero** responder hablando y que el agente repregunte sobre lo que dije
> **para** demostrar que entiendo mi proyecto de verdad.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E3 | XL (13) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Turno completo de conversación
  Dado que estoy en una sesión activa
  Cuando grabo mi respuesta y la envío
  Entonces veo mi respuesta transcrita en pantalla en menos de 4 segundos
  Y el agente responde con audio y texto en menos de 6 segundos (p95)
  Y su pregunta hace referencia explícita a algo que acabo de decir

Escenario: Audio vacío o inaudible
  Dado que estoy en una sesión activa
  Cuando envío un audio sin voz
  Entonces el agente me pide que repita, sin consumir una pregunta

Escenario: El agente nunca se sale del papel
  Dado que respondo algo confuso o fuera de tema
  Cuando el agente contesta
  Entonces nunca dice "no puedo continuar", "como IA" ni similares
  Y reconduce hacia el temario de la guía

Escenario: El agente no da la respuesta
  Dado que digo "no sé, dime tú la respuesta"
  Cuando el agente contesta
  Entonces no revela la respuesta correcta
  Y reformula la pregunta o pasa a la siguiente

Escenario: Cierre de la sustentación
  Dado que he respondido las 8 preguntas de la guía
  Cuando envío la última respuesta
  Entonces el agente cierra agradeciendo y señalando fortalezas y un área de mejora
  Y no revela ninguna nota
  Y la sesión pasa a estado PENDIENTE_REVISION

Escenario: No se almacena el audio crudo
  Dado que he terminado la sustentación
  Cuando reviso lo persistido en base de datos
  Entonces solo existen las transcripciones textuales, ningún fichero de audio
```

**INVEST** — **I:** depende de HU-08 · **N:** el número de preguntas y el tono son negociables · **V:** es el núcleo del producto · **E:** el mayor riesgo de estimación (XL) por la cadena STT→LLM→TTS · **S:** es la historia más grande; **candidata a dividir** en STT / conversación / TTS si no cabe en un sprint · **T:** los escenarios deterministas se automatizan; los de comportamiento del LLM se verifican con un juez LLM y revisión manual.

**Tickets:** [T-008](../03-tickets/T-008-canal-websocket-voz.md), [T-009](../03-tickets/T-009-motor-agente-guia.md)

---

### HU-10 — Reanudar una sesión interrumpida

> **Como** aprendiz
> **quiero** poder retomar donde iba si se me cae la conexión
> **para** no perder la sustentación por un problema de red.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🟠 Should-Have | E3 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Reconexión dentro de la ventana
  Dado que tenía una sesión activa en la pregunta 5 y se cortó la conexión
  Cuando vuelvo a entrar antes de 15 minutos
  Entonces retomo en la pregunta 5 con el historial de la conversación intacto

Escenario: Sesión caducada
  Dado que mi sesión lleva más de 60 minutos sin actividad
  Cuando intento reconectar
  Entonces la sesión se marca ABANDONADA
  Y se notifica al instructor para que decida si autoriza un nuevo intento
```

**INVEST** — **I:** depende de HU-09 · **N:** los tiempos son negociables · **V:** evita frustración y reclamaciones · **E:** requiere persistir el estado del turno · **S:** acotado · **T:** sí.

---

## E4 · Evaluación y rúbricas

### HU-11 — Definir la rúbrica de una guía

> **Como** instructor
> **quiero** definir mis propios criterios de evaluación con sus pesos
> **para** que todos mis aprendices se midan con la misma vara y sea la mía.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E4 | L (8) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Crear rúbrica
  Dado que soy instructor y tengo la guía "API REST de gestión de tareas"
  Cuando defino 5 criterios con nombre, descripción y peso que suman 100 %
  Entonces la rúbrica queda asociada a esa guía
  Y sustituye a cualquier criterio por defecto

Escenario: Los pesos deben sumar 100
  Dado que estoy editando una rúbrica
  Cuando los pesos suman 90 %
  Entonces recibo un 422 y no se guarda

Escenario: La rúbrica dirige la calificación del agente
  Dado que la rúbrica tiene el criterio "manejo de errores" con peso 30 %
  Cuando el agente califica una sesión de esa guía
  Entonces el reporte incluye una puntuación de 0 a 10 para "manejo de errores"
  Y ese criterio pondera un 30 % en la nota total

Escenario: Umbral de aprobación configurable
  Dado que fijo el umbral de la guía en 70 %
  Cuando una sesión obtiene 68 %
  Entonces se marca como NO APROBADA
```

**INVEST** — **I:** depende de HU-07 · **N:** escala 0-10 vs. niveles cualitativos, negociable · **V:** resuelve directamente P2 · **E:** CRUD anidado + cambio en el prompt de scoring · **S:** un recurso · **T:** sí.

**Tickets:** [T-010](../03-tickets/T-010-rubrica-configurable.md)

---

### HU-12 — Revisar y confirmar la calificación

> **Como** instructor
> **quiero** revisar la transcripción y la propuesta de nota del agente antes de publicarla
> **para** que la decisión final sea mía y pueda defenderla.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E4 | L (8) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Revisión y confirmación
  Dado que hay una sesión en estado PENDIENTE_REVISION
  Cuando la abro
  Entonces veo la transcripción íntegra, la puntuación propuesta por criterio y la nota resultante
  Y puedo modificar cualquier puntuación y escribir una retroalimentación
  Cuando confirmo
  Entonces la sesión pasa a CALIFICADA
  Y queda registrado quién confirmó, cuándo y qué puntuaciones cambió respecto a la propuesta

Escenario: Ninguna nota se publica sin humano
  Dado que una sesión terminó hace una semana sin que nadie la revisara
  Cuando el aprendiz consulta su resultado
  Entonces ve "Pendiente de revisión del instructor"
  Y en ningún caso ve la puntuación propuesta por el agente

Escenario: Solo el instructor de la ficha puede calificar
  Dado que soy instructor de otra ficha de la misma institución
  Cuando intento confirmar esta sesión
  Entonces recibo un 403

Escenario: Reclamación
  Dado que una sesión ya está CALIFICADA
  Cuando el aprendiz la marca como reclamada
  Entonces la sesión pasa a EN_RECLAMACION y se notifica al instructor
```

**INVEST** — **I:** depende de HU-09 y HU-11 · **N:** el detalle de la auditoría es negociable · **V:** es el requisito ético y legal innegociable (Art. 22 RGPD) · **E:** conocido · **S:** una pantalla + un endpoint · **T:** sí.

**Tickets:** [T-011](../03-tickets/T-011-revision-humana.md)

---

## E5 · Reportes y auditoría

### HU-13 — Consultar la retroalimentación

> **Como** aprendiz
> **quiero** ver mi nota por criterio y el comentario del instructor
> **para** saber exactamente qué debo reforzar.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🟠 Should-Have | E5 | S (3) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Consulta de resultado publicado
  Dado que mi sesión está CALIFICADA
  Cuando entro en "Mis resultados"
  Entonces veo la nota total, el desglose por criterio de la rúbrica
    y la retroalimentación escrita por el instructor
  Y puedo descargar mi transcripción

Escenario: No veo resultados de otros
  Dado que soy aprendiz
  Cuando intento consultar la sesión de un compañero
  Entonces recibo un 404
```

**INVEST** — **I:** depende de HU-12 · **N:** el formato de descarga es negociable · **V:** cierra el bucle de aprendizaje · **E:** trivial · **S:** una pantalla · **T:** sí.

---

### HU-14 — Panel de desempeño por ficha

> **Como** coordinadora académica
> **quiero** ver el desempeño agregado por criterio en una ficha
> **para** detectar en qué competencia falla el grupo y actuar sobre la formación.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔵 Could-Have | E5 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Agregado por criterio
  Dado que una ficha tiene 30 sesiones calificadas
  Cuando abro el panel de la ficha
  Entonces veo la media por criterio de la rúbrica, la tasa de aprobación
    y la distribución de notas

Escenario: Exportación
  Cuando pulso "Exportar"
  Entonces descargo un CSV con una fila por aprendiz y una columna por criterio
```

**INVEST** — **I:** depende de HU-12 · **N:** las métricas concretas son negociables · **V:** resuelve P5 · **E:** consultas de agregación · **S:** una pantalla · **T:** sí.

---

## E6 · Plataforma y despliegue

### HU-15 — Levantar el sistema con un comando

> **Como** técnico de TI del centro
> **quiero** levantar toda la plataforma con un solo comando
> **para** desplegarla sin ser experto en Python ni en bases de datos.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E6 | M (5) | `Por hacer` |

**Criterios de aceptación**

```gherkin
Escenario: Arranque limpio
  Dado un equipo con Docker instalado y el repositorio clonado
  Cuando ejecuto "docker compose up"
  Entonces se levantan API, base de datos y frontend
  Y las migraciones de Alembic se aplican solas
  Y "GET /api/v1/health" responde 200 en menos de 90 segundos

Escenario: Configuración por entorno
  Dado que copio ".env.example" a ".env" y ajusto las variables
  Cuando arranco el sistema
  Entonces usa esa configuración
  Y ningún secreto está escrito en el código ni versionado en git
```

**INVEST** — **I:** independiente · **N:** Compose vs. Kubernetes, negociable · **V:** condición para que exista despliegue · **E:** conocido · **S:** ficheros de infraestructura · **T:** verificable en CI.

---

### HU-16 — Voz del agente multiplataforma

> **Como** técnico de TI del centro
> **quiero** que el agente hable igual en Linux que en macOS
> **para** poder desplegar en el servidor del centro, que corre Linux.

| Prioridad | Épica | Estimación | Estado |
|---|---|---|---|
| 🔴 Must-Have | E6 | M (5) | `Por hacer` |

> 🐞 **Origen:** deuda técnica **D1** documentada en `DOCUMENTACION_TECNICA.md` §14 —
> la documentación prometía Piper pero el código usaba el comando `say` de macOS,
> dejando el sistema **inoperante fuera de macOS**.

**Criterios de aceptación**

```gherkin
Escenario: Síntesis en Linux
  Dado un contenedor Linux con Piper y la voz es_ES-davefx-medium instalados
  Cuando el agente sintetiza "Hola, cuéntame sobre tu proyecto"
  Entonces recibo audio WAV válido de más de 0 bytes

Escenario: Selección automática de motor
  Dado que Piper no está disponible en el sistema
  Cuando el agente sintetiza voz en macOS
  Entonces usa el comando "say" como reserva y el flujo no se interrumpe
  Y queda registrado en el log qué motor se usó

Escenario: Ningún motor disponible
  Dado que no hay ningún motor TTS instalado
  Cuando el agente intenta sintetizar
  Entonces la sesión continúa en modo solo texto
  Y el aprendiz ve un aviso de que no habrá audio
```

**INVEST** — **I:** aislada en el servicio de TTS · **N:** el motor de reserva es negociable · **V:** desbloquea el despliegue público, requisito de la entrega final · **E:** acotado · **S:** un módulo · **T:** sí, con CI en `ubuntu-latest`.

**Tickets:** [T-012](../03-tickets/T-012-tts-multiplataforma.md)

---

## Trazabilidad historias ↔ problemas ↔ KPIs

| Historia | Problema que resuelve | KPI que mueve |
|---|---|---|
| HU-01, HU-02, HU-04 | Habilitadores | — |
| HU-03 | R1 (datos personales) | K8 |
| HU-05, HU-06, HU-07 | P1 | K1 |
| HU-08, HU-10 | P1, P6 | K1, K6 |
| HU-09 | P1, P4 | K3, K6, K7 |
| HU-11 | P2 | K4, K5 |
| HU-12 | P2, P3 | K2, K4, K5 |
| HU-13 | P3 | K7 |
| HU-14 | P5 | — |
| HU-15, HU-16 | R2, R4 | K1 |
