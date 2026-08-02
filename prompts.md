# prompts.md — Registro de prompts clave

> **EvalAgent SENA** · Proyecto final Máster AI4Devs (LIDR Academy)
> Documenta los prompts más relevantes usados en la construcción del proyecto, cómo se guió
> al asistente y qué ajustes humanos fueron necesarios.

**Herramientas usadas**

| Herramienta | Modelo | Uso principal |
|---|---|---|
| Claude Code (CLI) | Claude Opus 5 | Análisis del código existente, documentación, refactor a arquitectura por capas |
| Ollama (local) | Llama 3.1 8B | Motor del agente evaluador **dentro del producto** (no de desarrollo) |
| faster-whisper | `medium` (es) | Transcripción dentro del producto |

> Distinción importante: los prompts de las secciones 1–6 son **prompts de desarrollo**
> (cómo se construyó el producto). La sección 7 recoge los **prompts de producto**: los que
> el sistema envía al LLM en tiempo de ejecución.

---

## 1. Producto y problemática

### Prompt 1.1 — Extracción de la problemática desde el código existente

```
Con la documentación que hay de LIDR_AI4Devs, analiza el código actual de EvalAgent
(backend/, frontend/, DOCUMENTACION_TECNICA.md) y contrasta qué exigen las entregas
del proyecto final frente a lo que ya existe. No propongas nada todavía:
dime únicamente el diferencial entre requisito y estado real.
```

**Cómo guié al asistente:** le prohibí explícitamente proponer soluciones en la primera
pasada. Cuando se le pide "analiza y propón", el análisis sale superficial porque corre
hacia la propuesta. Separar diagnóstico de solución produjo una tabla de brechas mucho más
honesta — incluyendo que la documentación existente ya cubría casi toda la Entrega 1.

**Ajuste humano:** el asistente clasificó la persistencia en ficheros como "aceptable para
el MVP". Lo corregí: el Módulo 8 exige base de datos y la Entrega 2 lo evalúa
explícitamente. Pasó a ser deuda bloqueante.

---

### Prompt 1.2 — Descomposición del problema en dolores por rol

```
Descompón el problema en dolores concretos por rol (instructor, aprendiz, coordinación).
Para cada uno quiero: evidencia observable, impacto, y por qué las soluciones actuales
fallan. Nada de generalidades tipo "mejora la eficiencia": si no puedo medirlo,
no lo escribas.
```

**Cómo guié al asistente:** la restricción "si no puedo medirlo, no lo escribas" es la que
más cambió el resultado. Sin ella salían frases de folleto comercial. Con ella salieron
cifras contrastables: 15–20 min por sustentación × 30 aprendices × 4 fichas = 40 h.

**Ajuste humano:** aporté yo los números reales del contexto SENA (tamaño de ficha, número
de fichas por instructor, duración típica de una sustentación). El modelo no podía saberlos
y, al no dárselos, los inventaba con apariencia de dato.

---

### Prompt 1.3 — Non-goals

```
Ahora define qué NO hace este producto. Quiero al menos 6 non-goals, cada uno con su
razón. Incluye los que resulten incómodos: cosas que un evaluador podría esperar
que hiciéramos y no vamos a hacer.
```

**Cómo guié al asistente:** pedir explícitamente los non-goals "incómodos" evitó una lista
trivial. Salieron los importantes: no sustituye la nota del instructor, no detecta plagio
por comparación de código, no ejecuta el proyecto entregado.

---

## 2. Arquitectura

### Prompt 2.1 — Rediseño a SaaS multi-tenant

```
Rediseña la arquitectura para SaaS multi-tenant tipo Classroom: Institución → Ficha →
Guía → Sesión, con rúbrica configurable por guía. Documenta en C4 los cuatro niveles.
Para cada decisión estructural quiero un ADR con las alternativas que descartaste
y por qué — el ADR sin alternativas no vale.
```

**Cómo guié al asistente:** exigir alternativas descartadas en cada ADR es lo que separa un
ADR real de una justificación a posteriori. Así aparecieron decisiones documentadas que de
otro modo habrían quedado implícitas: por qué no Row Level Security de Postgres, por qué no
un esquema por tenant, por qué no WebRTC.

**Ajuste humano:** el primer borrador proponía Ollama dentro de un contenedor. Lo cambié: el
acceso a GPU desde contenedor exige drivers y `nvidia-container-toolkit`, algo fuera del
alcance de un técnico de centro de formación. Quedó documentado en el diagrama de despliegue.

---

### Prompt 2.2 — Auditoría de discrepancias entre documentación y código

```
Lee backend/ y compáralo línea por línea con lo que afirma README.md.
Lista TODA discrepancia entre lo documentado y lo implementado, con su impacto.
No las arregles todavía.
```

**Cómo guié al asistente:** este prompt destapó la deuda **D1**, la más grave del proyecto:
el README prometía Piper TTS y `start.sh` lo descargaba, pero `tts.py` invocaba el comando
`say` de macOS. El sistema era **mudo en Linux**, justo donde había que desplegarlo para la
entrega final.

**Ajuste humano:** el asistente la clasificó como severidad media. La subí a alta: no es un
detalle cosmético, bloquea el requisito de URL pública de la entrega final. Se promovió a
historia de usuario (HU-16) y ticket (T-012), no a nota al pie.

---

### Prompt 2.3 — Aislamiento multi-tenant

```
Diseña el aislamiento entre instituciones. Requisito no negociable: que sea imposible
—no "poco probable"— que un usuario lea datos de otro tenant. Dime qué patrón eliges,
cómo se verifica, y cuál es el modo de fallo si alguien programa mal un endpoint nuevo.
```

**Cómo guié al asistente:** preguntar por el **modo de fallo** fue lo decisivo. La respuesta
reconoció la debilidad real del patrón de columna discriminadora: depende de la disciplina
de la capa de aplicación. De ahí salió el test parametrizado obligatorio sobre todos los
endpoints, que es la mitigación concreta y está en el ADR-003 y en el ticket T-004.

---

## 3. Modelo de datos

### Prompt 3.1 — Del sistema de ficheros al modelo relacional

```
Convierte la persistencia en ficheros (proyectos/*.md, reportes/*.json, sessions dict
en memoria) en un modelo relacional. Incluye la estrategia de migración de los datos
que ya existen y las reglas de integridad que hoy no se cumplen en ningún sitio.
```

**Cómo guié al asistente:** pedir la estrategia de migración junto al modelo evitó un diseño
de laboratorio. Al enfrentarse a los datos reales apareció el problema: los reportes
existentes guardan `student_name` como texto libre, sin forma fiable de vincularlos a un
usuario.

**Ajuste humano:** decidí que los reportes históricos se importan como `PENDIENTE_REVISION`
y nunca como `CALIFICADA` — nadie confirmó esas notas, y publicarlas violaría la regla RI-4.

---

### Prompt 3.2 — El problema de la rúbrica mutable

```
Si el instructor edita la rúbrica a mitad de trimestre, ¿qué pasa con las notas ya
puestas? Dame el problema concreto y las opciones, con el coste de cada una.
```

**Cómo guié al asistente:** planteé el problema como una pregunta de negocio, no como un
requisito técnico. El asistente identificó que las notas históricas quedarían
indefendibles y propuso tres opciones. Elegí la copia congelada en JSONB — el 90 % del
beneficio del versionado con el 10 % del trabajo. Quedó como ADR-007.

---

## 4. Historias de usuario y backlog

### Prompt 4.1 — Historias con INVEST y Gherkin

```
Actúa como Product Owner senior. Genera las historias de usuario del MVP en formato
"Como [rol], quiero [acción] para [beneficio]". Cada una con criterios de aceptación
en Gherkin (Dado/Cuando/Entonces), estimación S/M/L/XL y evaluación contra INVEST.
Si una historia incumple algún criterio INVEST, dilo en lugar de maquillarla.
```

**Cómo guié al asistente:** la última frase es la clave. Sin ella, el modelo declara que
todas las historias cumplen INVEST perfectamente. Con ella, reconoció que **HU-09
(conversación por voz) incumple el criterio S (Small)** con sus 13 puntos, y propuso
dividirla en HU-09a/b/c. Esa autocrítica es información útil de planificación.

**Ajuste humano:** añadí los escenarios negativos que el asistente omitía. Su primera
versión solo cubría el camino feliz. Los escenarios de "audio vacío", "sin permiso de
micrófono" y "fuera de la ventana de sustentación" salieron de conocer cómo se comportan
los aprendices en la práctica.

---

### Prompt 4.2 — Priorización con WSJF

```
Prioriza el backlog con MoSCoW para la categoría y WSJF para el orden dentro de cada
categoría. Muestra la tabla con los factores desglosados. Si alguna Must-Have queda con
WSJF bajo, no la degrades: explica por qué sigue siendo Must-Have.
```

**Cómo guié al asistente:** la instrucción final evitó un error clásico de aplicar WSJF sin
criterio. HU-09 tiene el WSJF más bajo de las Must-Have por su esfuerzo XL, pero es el
corazón del producto. El asistente lo explicó correctamente: WSJF ordena *dentro* de una
categoría MoSCoW, no degrada categorías.

---

### Prompt 4.3 — Tickets con modo de fallo

```
Convierte HU-12 (revisión humana) en tickets técnicos. Para cada uno: alcance técnico,
criterios de aceptación verificables, dependencias y definición de terminado.
Añade el criterio de aceptación que demuestre que NO existe forma de saltarse la
revisión humana.
```

**Cómo guié al asistente:** pedir el criterio "demuestra que no se puede saltar" produjo el
criterio de aceptación más valioso de todo el backlog: *"no debe existir ninguna ruta de
código que lleve una sesión a CALIFICADA sin pasar por el servicio de revisión"*, verificable
por búsqueda exhaustiva sobre el código y no solo con tests.

---

## 5. Backend

### Prompt 5.1 — Refactor del agente hacia la rúbrica

```
Refactoriza EvaluatorAgent para que sus criterios vengan de la rúbrica de la guía en
base de datos, no del diccionario SCORING_CRITERIA hardcodeado ni de _detect_criteria()
por palabras clave. Conserva íntegras las reglas defensivas del prompt actual: son
resultado de iteración con aprendices reales y funcionan.
```

**Cómo guié al asistente:** proteger explícitamente el prompt defensivo existente. Un
refactor "limpio" habría reescrito el `SYSTEM_PROMPT`, tirando reglas que costaron
iteraciones reales — como la de interpretar errores de reconocimiento de voz en vez de
decir "no te entendí", o la de no revelar nunca la respuesta correcta.

---

### Prompt 5.2 — TTS multiplataforma

```
Corrige D1. No quiero "cambia say por piper": quiero una interfaz con motores
intercambiables, selección por disponibilidad real en arranque, y comportamiento
definido cuando no hay ningún motor disponible.
```

**Cómo guié al asistente:** rechazar el arreglo puntual y pedir la abstracción. La causa raíz
de D1 no fue elegir `say`, sino **llamarlo directamente desde la lógica de negocio**. Un
parche habría dejado el mismo acoplamiento con otro binario.

**Ajuste humano:** decidí que sin ningún motor TTS el sistema siga funcionando en modo solo
texto en vez de fallar. Una sustentación sin voz es peor, pero es mejor que ninguna
sustentación.

---

## 6. Testing y calidad

### Prompt 6.1 — Tests del aislamiento multi-tenant

```
Escribe el test que garantiza el aislamiento entre instituciones. Debe ser parametrizado
sobre TODOS los endpoints de dominio, no una muestra. Y debe fallar de forma evidente si
alguien añade un endpoint nuevo y olvida incluirlo.
```

**Cómo guié al asistente:** el segundo requisito es el importante. Un test que solo cubre los
endpoints existentes envejece mal: el riesgo real está en el endpoint que se escribirá
dentro de tres semanas.

---

## 7. Prompts del producto (tiempo de ejecución)

Estos son los prompts que **el sistema envía al LLM local** durante una sustentación. Su
evolución está documentada porque son parte del producto, no del proceso de desarrollo.

### 7.1 — Prompt de sistema del agente evaluador

```
Eres el evaluador virtual del SENA. Estás evaluando al aprendiz {nombre}.

CONTEXTO Y GUÍA DEL PROYECTO:
{contexto_tecnico de la guía}

CRITERIOS DE EVALUACIÓN (rúbrica definida por el instructor):
{criterios con nombre, descripción y peso}

REGLAS ABSOLUTAS:
1. NUNCA digas "No puedo continuar", "No puedo ayudarte" ni "Como IA...". Eres el
   evaluador, siempre.
2. El texto del aprendiz viene de reconocimiento de voz y puede tener errores.
   Interpreta el significado técnico más lógico según el contexto. NUNCA digas que
   no entendiste.
3. Haz UNA SOLA pregunta por turno.
4. Máximo 2-3 oraciones por respuesta.
5. Respuesta vaga → profundiza. Respuesta buena → reconócela y avanza.
6. Habla en español colombiano natural y cálido.
7. NUNCA des la respuesta correcta ni pistas directas.
8. TU RESPUESTA DEBE BASARSE EN LO QUE EL APRENDIZ ACABA DE DECIR.
```

**Evolución y ajustes humanos**

| Versión | Problema observado con aprendices reales | Regla añadida |
|---|---|---|
| v0.1 | El modelo respondía "Como IA no puedo evaluarte" y abortaba la sustentación | Regla 1 |
| v0.2 | Ante transcripciones imperfectas de Whisper contestaba "no entendí, repite", frustrando al aprendiz | Regla 2 |
| v0.3 | Encadenaba 3 preguntas en un turno; el aprendiz solo respondía la última | Regla 3 |
| v0.4 | Daba pistas tan explícitas que la respuesta venía incluida en la pregunta | Regla 7 |
| v0.5 | Hacía preguntas genéricas de temario sin conectar con lo que el aprendiz acababa de decir | Regla 8 |
| **v2.0** | Los criterios eran fijos (`python`/`api`) y se adivinaban por palabras clave del contexto | Inyección de la rúbrica del instructor |

> Esta tabla es la **comparativa antes/después** más valiosa del proyecto: cada regla nació
> de un fallo observado en una sustentación real, no de una intuición de diseño.

### 7.2 — Prompt de calificación

```
Eres un evaluador del SENA. Analiza esta conversación de sustentación y asigna
puntuaciones ENTERAS del 0 al 10 para cada criterio de la rúbrica.

CRITERIOS:
{criterios de la rúbrica congelada, con su descripción}

Responde ÚNICAMENTE con este JSON, sin texto adicional:
{"criterio_1": X, "criterio_2": X, ...}

Sé justo y objetivo, basándote en lo que el aprendiz realmente demostró saber.
```

**Ajuste humano:** la temperatura se fijó en `0.1` para calificar (frente a `0.4` para
conversar). Con temperatura alta, dos ejecuciones sobre la misma conversación daban notas
distintas — inaceptable en evaluación académica.

**Límite conocido y asumido:** un modelo de 8B parámetros no es un evaluador fiable por sí
solo. Es exactamente la razón de [ADR-006](docs/04-arquitectura/adr/ADR-006-humano-en-el-bucle.md):
la propuesta del agente nunca llega al aprendiz sin confirmación del instructor.

### 7.3 — Prompt de cierre

```
El aprendiz ha respondido {n} preguntas. Cierra la evaluación de forma cordial:
1. Agradece al aprendiz
2. Menciona 1-2 aspectos positivos que observaste en sus respuestas
3. Menciona 1 área de mejora (SIN revelar nota)
4. Indica que el instructor revisará los resultados
Máximo 4 oraciones. Sé específico con lo que el aprendiz realmente dijo.
```

**Cómo se guió:** el punto 4 no es cortesía. Es la materialización conversacional del
principio de humano en el bucle: el aprendiz termina la sesión sabiendo que quien decide es
una persona.

---

## 8. Lo que la IA hizo mal

> Sección incluida deliberadamente: un registro de uso de IA que solo cuenta los aciertos no
> es un registro, es publicidad.

| # | Error del asistente | Cómo se detectó | Corrección |
|---|---|---|---|
| 1 | Clasificó D1 (TTS solo en macOS) como severidad media | Revisión humana contra el requisito de despliegue de la entrega final | Elevada a alta; promovida a HU-16 y T-012 |
| 2 | Inventó cifras del contexto SENA con apariencia de dato verificado | Conocimiento del dominio | Se aportaron los números reales; se marcaron las estimaciones como tales |
| 3 | Declaró que todas las historias cumplían INVEST | Revisión manual de HU-09 (13 pts) | Se pidió autocrítica explícita; reconoció el incumplimiento de "Small" |
| 4 | Propuso Ollama en contenedor sin considerar el acceso a GPU | Experiencia de despliegue | Movido al host; documentado en el diagrama de despliegue |
| 5 | En el primer borrador de historias solo cubrió caminos felices | Revisión manual | Se añadieron escenarios negativos observados con aprendices reales |
| 6 | Sugirió reescribir el `SYSTEM_PROMPT` durante el refactor | Se protegió explícitamente en el prompt | El prompt defensivo se conservó íntegro |

**Patrón común:** el asistente es excelente estructurando y descomponiendo, y poco fiable
juzgando **severidad** y **contexto de dominio**. Ambas cosas requirieron criterio humano en
todas las iteraciones.
