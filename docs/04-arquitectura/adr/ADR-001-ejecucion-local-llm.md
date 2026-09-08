# ADR-001 · Ejecución 100 % local de la IA

**Estado:** ✅ Aceptada · **Fecha:** 2026-07-26 · **Decisor:** Teo

## Contexto

El sistema procesa la voz de aprendices del SENA, muchos de ellos menores de edad. La voz es
un dato biométrico y las respuestas contienen información académica personal. La Ley
1581/2012 (Habeas Data) exige base legal y control sobre el tratamiento; enviar audio de
menores a un proveedor extranjero implica transferencia internacional de datos con todo lo
que arrastra.

Además, los centros de formación regionales tienen conectividad intermitente (restricción
**R2**) y presupuesto de licencias prácticamente nulo (**R3**).

## Decisión

**Todo el procesamiento de IA se ejecuta en la infraestructura del centro:**

- **STT:** faster-whisper, modelo `medium`, en el propio proceso de la API.
- **LLM:** Ollama con Llama 3.1 8B, en el host.
- **TTS:** Piper, como subproceso.

**No se realiza ninguna llamada a APIs de IA de terceros.**

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| OpenAI Whisper API + GPT-4 | Mejor calidad, pero transfiere voz de menores fuera del país. Coste por token incompatible con R3. |
| Claude / Gemini vía API | Mismo problema de transferencia. Además, dependencia de conectividad (R2). |
| Modelo propio afinado en la nube privada del SENA | Ideal a largo plazo, pero exige infraestructura y equipo que hoy no existen. |
| Híbrido: STT local + LLM en la nube | La transcripción ya contiene el contenido sensible. No resuelve nada y añade complejidad. |

## Consecuencias

**Positivas**
- Cumplimiento de la Ley 1581/2012 sin negociar un contrato de encargo de tratamiento.
- Coste marginal por sustentación = 0. Sustentar 100 o 10.000 veces cuesta lo mismo.
- Funciona sin conexión a internet.
- Es la **ventaja competitiva injusta** del Lean Canvas: un SaaS sobre OpenAI no puede prometer esto.

**Negativas**
- Calidad conversacional inferior a la de un modelo frontera. Mitigación: prompts muy dirigidos y anclados a la guía.
- Requiere hardware con 16–32 GB de RAM en el centro (riesgo **RG-4**). Mitigación: perfil degradado configurable.
- La latencia depende del hardware local, no de un SLA de proveedor.
- Mantener modelos actualizados es responsabilidad del centro.

## Verificación

Auditoría de dependencias de red: la suite de tests corre con salida a internet bloqueada y
debe pasar íntegra (RNF-03).
