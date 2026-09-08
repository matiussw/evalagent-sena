# ADR-005 · TTS como interfaz con motores intercambiables

**Estado:** ✅ Aceptada · **Fecha:** 2026-08-02 · **Corrige:** deuda técnica **D1**

## Contexto

La v1 documentaba Piper como motor de síntesis de voz — el README lo anunciaba y `start.sh`
lo descargaba — pero `backend/tts.py` invocaba directamente el comando `say` de macOS.

Consecuencia: **el sistema era mudo en Linux**, que es exactamente donde hay que desplegarlo
para tener una URL pública. La discrepancia estaba documentada como **D1** y bloqueaba la
entrega final.

La causa de fondo no fue el binario elegido, sino que el código llamaba a un comando del
sistema operativo directamente, sin abstracción que permitiera sustituirlo.

## Decisión

**Definir una interfaz `MotorTTS`** con tres implementaciones:

| Motor | Plataforma | Prioridad |
|---|---|---|
| `PiperTTS` | Linux, macOS, Windows | 1ª — es el motor de referencia |
| `SayTTS` | macOS | 2ª — reserva en desarrollo local |
| `EspeakTTS` | Linux | 3ª — reserva de emergencia |

- La selección ocurre **en el arranque**, comprobando disponibilidad real de los binarios.
- `TTS_ENGINE` fuerza un motor concreto (indispensable para tests deterministas).
- Si no hay ningún motor, el sistema **no falla**: sigue en modo solo texto y lo avisa en la
  interfaz. Una sustentación sin voz es peor, pero es mejor que ninguna sustentación.
- El motor activo se expone en `/api/v1/health`.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Solo Piper, sin reserva | Más simple, pero una instalación incompleta deja el sistema mudo sin diagnóstico claro. |
| TTS en el navegador (`SpeechSynthesis`) | Cero infraestructura, pero la voz varía por navegador y sistema operativo — la experiencia sería inconsistente entre aprendices, lo que choca con el principio de evaluación uniforme. |
| API de TTS en la nube | Viola [ADR-001](ADR-001-ejecucion-local-llm.md). |

## Consecuencias

**Positivas**
- Desbloquea el despliegue en Linux y, con ello, la entrega final.
- La misma voz para todos los aprendices: coherente con la uniformidad de criterio.
- Los tests simulan el motor y no dependen de binarios instalados.
- Añadir un motor nuevo es implementar una interfaz.

**Negativas**
- Tres rutas de código que mantener y probar.
- Piper exige descargar el modelo de voz (~60 MB) en la imagen Docker.
- La selección automática puede sorprender: por eso se registra en el log y se expone en `/health`.

## Lección aprendida

La deuda D1 no se originó al elegir `say`, sino al **llamarlo directamente desde la lógica
de negocio**. Toda dependencia del sistema operativo debe entrar por una interfaz.
