# T-012 · TTS multiplataforma con Piper

| Campo | Valor |
|---|---|
| **Tipo** | 🐞 Bug / deuda técnica **D1** |
| **Historia** | [HU-16](../02-backlog/02-historias-usuario.md#hu-16--voz-del-agente-multiplataforma) |
| **Épica** | E6 · Plataforma y despliegue |
| **Prioridad** | 🔴 Alta |
| **Estimación** | 5 pts |
| **Componente** | `backend/app/services/tts.py` |
| **Estado** | `Por hacer` |

## Descripción

**El defecto:** el README y `start.sh` afirman que el sistema usa Piper con la voz
`es_ES-davefx-medium`, e incluso `start.sh` descarga Piper. Pero `backend/tts.py` invoca el
comando `say` de macOS. Resultado: **el sistema es mudo en Linux**, que es justamente donde
hay que desplegarlo para la entrega final.

**Impacto:** bloquea HU-15 y el requisito de URL pública de la entrega final.

## Alcance técnico

- Interfaz `MotorTTS` con implementaciones: `PiperTTS`, `SayTTS` (macOS), `EspeakTTS` (Linux).
- Selección en arranque por disponibilidad real, con orden Piper → say → espeak-ng.
- Variable `TTS_ENGINE` para forzar un motor concreto (útil en tests).
- Salida WAV en base64, formato único para todos los motores.
- Si no hay ningún motor, el sistema sigue funcionando en **modo solo texto** y lo avisa.
- El motor elegido se registra en el log y se expone en `/api/v1/health`.
- Piper y su voz se instalan en la imagen Docker.

## Criterios de aceptación

- [ ] En un contenedor Linux con Piper, sintetizar devuelve WAV válido de más de 0 bytes.
- [ ] Sin Piper y en macOS, el sistema cae a `say` y lo registra en el log.
- [ ] Sin ningún motor, la sesión continúa en modo solo texto con aviso en la interfaz.
- [ ] `TTS_ENGINE=piper` con Piper ausente falla al arrancar, de forma explícita.
- [ ] `GET /api/v1/health` informa del motor activo.
- [ ] La suite pasa en `ubuntu-latest` en CI (RNF-08).
- [ ] README y documentación técnica reflejan el comportamiento real.

## Definición de terminado

Tests por motor con el binario simulado · CI en verde en Ubuntu · deuda **D1** cerrada ·
documentación corregida.

## Dependencias

Ninguna — se puede abordar en paralelo. **Bloquea:** HU-15 y el despliegue público.
