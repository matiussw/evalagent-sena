# 01 — Problemática a resolver

> **Documento de contexto de producto** — EvalAgent SENA
> Estado: `Aprobado` · Versión: `2.0` · Sustituye a la sección 2.1 de `DOCUMENTACION_TECNICA.md`

---

## 1. Contexto

El programa **ADSO** (Análisis y Desarrollo de Software) del SENA forma técnicos y tecnólogos
en desarrollo de software. Uno de los instrumentos de evaluación obligatorios es la
**sustentación oral**: el aprendiz explica de viva voz su proyecto ante el instructor, quien
verifica que *comprende* lo que entregó y no se limitó a copiarlo.

Cada instructor gestiona entre **3 y 6 fichas** simultáneas, con **25–35 aprendices por ficha**.
Esto arroja entre **75 y 210 sustentaciones por trimestre y por instructor**.

---

## 2. El problema

> **Los instructores no tienen tiempo material para sustentar oralmente a todos sus aprendices,
> y cuando lo hacen, el resultado no es comparable entre ellos.**

### 2.1 Descomposición del problema

| # | Problema | Evidencia / Manifestación | Impacto |
|---|---|---|---|
| **P1** | **Cuello de botella temporal** | 15–20 min por sustentación × 30 aprendices = 7,5–10 h por ficha. Con 4 fichas: hasta 40 h, una semana completa dedicada solo a sustentar. | 🔴 Crítico |
| **P2** | **Inconsistencia de criterio** | El instructor pregunta distinto al aprendiz 1 que al 28 (fatiga, sesgo de simpatía, efecto de anclaje con el anterior). No hay rúbrica aplicada de forma uniforme. | 🔴 Crítico |
| **P3** | **Ausencia de evidencia auditable** | La sustentación se hace de palabra. No queda transcripción ni registro de qué se preguntó ni qué respondió el aprendiz. Ante una reclamación, no hay nada que revisar. | 🟠 Alto |
| **P4** | **Detección tardía de la copia** | Con IA generativa, entregar código ajeno es trivial. La única barrera real es la sustentación oral — que es justamente lo que se está saltando por falta de tiempo. | 🔴 Crítico |
| **P5** | **Cero trazabilidad longitudinal** | No se puede responder "¿en qué competencia falla sistemáticamente esta ficha?" porque no hay datos históricos estructurados. | 🟡 Medio |
| **P6** | **Barrera de agenda** | Cuadrar horario aprendiz-instructor es un problema logístico, sobre todo en formación virtual y en jornadas nocturnas. | 🟡 Medio |

### 2.2 Cómo se resuelve hoy (y por qué no funciona)

| Práctica actual | Por qué falla |
|---|---|
| Sustentación oral presencial completa | No escala. Es el problema P1. |
| Sustentación por muestreo (solo a algunos) | Elimina el efecto disuasorio: si solo sustenta 1 de cada 5, copiar sigue siendo rentable. |
| Sustentación escrita / cuestionario | Se responde con IA. No verifica comprensión oral ni permite repreguntar. |
| Videollamada grabada | Genera evidencia, pero no reduce el tiempo del instructor: sigue teniendo que estar presente. |
| Defensa grupal | Los aprendices con menor dominio se esconden detrás del compañero fuerte. |

---

## 3. Los tres dolores por rol

### 👨‍🏫 Instructor — *Carolina, 41 años, instructora ADSO*
> «Tengo 118 aprendices este trimestre. Si sustento a todos me quedo sin semana.
> Y cuando llego al aprendiz número 25 ya no pregunto igual que al primero —
> sé que no es justo, pero es humano.»

- **Dolor principal:** el tiempo. Sustentar bien es incompatible con el volumen.
- **Dolor secundario:** no puede defender una nota si el aprendiz reclama.

### 👩‍🎓 Aprendiz — *Jhon, 19 años, aprendiz ADSO ficha 2758421*
> «Estudié un montón y me tocó sustentar de últimas, cuando el profe ya estaba
> cansado. Me hizo dos preguntas y ya. Al de al lado le hizo diez.»

- **Dolor principal:** la evaluación que recibe depende de cuándo le toque el turno.
- **Dolor secundario:** no recibe retroalimentación concreta sobre qué no supo explicar.

### 🏛️ Coordinación académica — *Área de formación del centro*
> «Cuando pido evidencias de evaluación para la auditoría de calidad,
> lo que me llega son planillas de notas. La evidencia del proceso no existe.»

- **Dolor principal:** no hay evidencia auditable del proceso evaluativo.
- **Dolor secundario:** no puede medir el desempeño agregado por competencia ni por ficha.

---

## 4. Non-goals — Lo que este producto **no** resuelve

Delimitar el alcance es parte de definir el problema. EvalAgent **no** pretende:

| # | Fuera de alcance | Razón |
|---|---|---|
| NG-1 | **Sustituir al instructor en la nota final** | El agente produce una *propuesta* de calificación. La nota la confirma o corrige siempre un humano. Es un requisito ético y normativo (ver [ADR-006](../04-arquitectura/adr/ADR-006-humano-en-el-bucle.md)). |
| NG-2 | **Detectar plagio comparando código** | Existen herramientas específicas (MOSS, JPlag). EvalAgent verifica *comprensión*, no *similitud textual*. |
| NG-3 | **Evaluar la ejecución del software entregado** | No compila, no ejecuta ni testea el proyecto del aprendiz. Evalúa el discurso técnico sobre él. |
| NG-4 | **Ser un LMS** | No gestiona contenidos, matrículas oficiales, asistencia ni certificados. Se integra con Sofía Plus / Territorium, no los reemplaza. |
| NG-5 | **Videoconferencia o proctoring por cámara** | Solo audio. Sin reconocimiento facial ni vigilancia biométrica — decisión deliberada de privacidad. |
| NG-6 | **Evaluar en idiomas distintos del español** | El MVP se ciñe a español (es-CO). |

---

## 5. Restricciones que condicionan la solución

| # | Restricción | Origen | Consecuencia de diseño |
|---|---|---|---|
| **R1** | Los datos de aprendices son **datos personales de menores en algunos casos** | Ley 1581/2012 (Colombia, Habeas Data) + RGPD como referencia | Procesamiento local por defecto, sin envío a APIs de terceros. Ver [ADR-001](../04-arquitectura/adr/ADR-001-ejecucion-local-llm.md). |
| **R2** | Conectividad intermitente en centros de formación regionales | Realidad operativa del SENA | El motor de IA debe poder correr on-premise, no depender de la nube. |
| **R3** | Presupuesto de licencias ≈ 0 | Entidad pública | Todo el stack debe ser software libre o de coste nulo. |
| **R4** | El instructor no es administrador de sistemas | Perfil del usuario | Instalación y operación deben ser de un solo comando. |
| **R5** | Decisión automatizada sobre una persona | Art. 22 RGPD / AI Act (sistema de alto riesgo en educación) | Obligatorio: humano en el bucle, derecho a explicación, derecho a impugnar. |

---

## 6. Oportunidad

> Si una sustentación de 15 minutos pasa de consumir **15 minutos de instructor**
> a consumir **3 minutos de revisión asíncrona**, un instructor con 118 aprendices
> pasa de **~30 horas** a **~6 horas** por trimestre.

Esto no solo ahorra tiempo: **permite sustentar al 100 % de los aprendices**, lo que
restaura el efecto disuasorio frente a la copia (P4) y elimina la arbitrariedad del
muestreo.

---

## 7. Métricas de éxito

Ver el detalle con líneas base y objetivos en [`02-prd.md` §9](02-prd.md#9-métricas-de-éxito-kpis).

| KPI | Línea base | Objetivo MVP |
|---|---|---|
| Cobertura de sustentación | ~35 % de aprendices | ≥ 95 % |
| Tiempo de instructor por sustentación | 15–20 min | ≤ 3 min (revisión) |
| Sustentaciones con evidencia auditable | 0 % | 100 % |
| Correlación nota-agente ↔ nota-instructor | n/a | ≥ 0,75 (Pearson) |

---

## Trazabilidad

| Problema | Épica que lo ataca | Historias de usuario |
|---|---|---|
| P1 Cuello de botella | [E2](../02-backlog/01-epicas.md#e2--gestión-académica) · [E3](../02-backlog/01-epicas.md#e3--sustentación-por-voz) | HU-07, HU-08, HU-09 |
| P2 Inconsistencia | [E4](../02-backlog/01-epicas.md#e4--evaluación-y-rúbricas) | HU-05, HU-11 |
| P3 Sin evidencia | [E5](../02-backlog/01-epicas.md#e5--reportes-y-auditoría) | HU-12, HU-13 |
| P4 Copia | [E3](../02-backlog/01-epicas.md#e3--sustentación-por-voz) | HU-09, HU-10 |
| P5 Sin trazabilidad | [E5](../02-backlog/01-epicas.md#e5--reportes-y-auditoría) | HU-14 |
| P6 Agenda | [E3](../02-backlog/01-epicas.md#e3--sustentación-por-voz) | HU-08 |

---

*Documento elaborado siguiendo los lineamientos del Módulo 4 y 5 del Máster AI4Devs (LIDR Academy).*
