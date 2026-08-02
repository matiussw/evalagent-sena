# EvalAgent SENA 🤖
### Agente de Sustentación Oral para Proyectos API

Sistema de evaluación oral automática para estudiantes del programa ADSO.
El agente hace preguntas técnicas por voz, transcribe las respuestas con Whisper
y genera un reporte al final.

---

## Arquitectura

```
Estudiante (browser) ──── WebSocket ──── FastAPI
     │                                      │
  WebRTC mic                         Whisper STT (local)
  Audio playback                     Ollama LLM (local)
                                     Piper TTS (local)
```

## Stack
| Componente | Tecnología |
|---|---|
| Backend | FastAPI + WebSocket |
| STT | faster-whisper (modelo: small) |
| LLM | Ollama + Llama 3.1 8B |
| TTS | Piper (voz: es_ES-davefx-medium) |
| Frontend | HTML + WebRTC (sin frameworks) |

---

## Setup rápido

```bash
# 1. Clonar / copiar el proyecto
cd evaluador-agente

# 2. Dar permisos y ejecutar setup automático
chmod +x start.sh
./start.sh
```

El script instala automáticamente:
- Dependencias Python (faster-whisper, FastAPI, etc.)
- Piper TTS + modelo de voz español
- Verifica Ollama y descarga llama3.1:8b si no está

---

## Agregar proyectos de estudiantes

Crea archivos `.md` en la carpeta `proyectos/`:

```bash
# Ejemplo
nano proyectos/nombre-del-proyecto.md
```

El archivo debe describir:
- Tecnologías usadas
- Endpoints implementados
- Modelo de datos
- Decisiones de diseño

El agente usará este contexto para hacer preguntas específicas.

---

## Exponer a estudiantes (URL pública)

### Opción A: ngrok (más fácil)
```bash
# Terminal 1
./start.sh

# Terminal 2
ngrok http 8000
# → Copia la URL: https://xxxx.ngrok.io
```

### Opción B: Cloudflare Tunnel (gratuito, sin límites)
```bash
# Instalar
brew install cloudflared   # macOS
# o: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Ejecutar (en otra terminal mientras corre el backend)
cloudflared tunnel --url http://localhost:8000
# → URL permanece activa mientras corra el proceso
```

### Opción C: Red local (mismo WiFi)
```bash
# Obtener IP local
ipconfig getifaddr en0   # macOS
ip route get 1 | awk '{print $7}'  # Linux

# Compartir: http://192.168.x.x:8000
```

---

## Configuración

### Cambiar modelo LLM
Edita `backend/agent.py`:
```python
OLLAMA_MODEL = "mistral:7b"  # o phi3, gemma2, etc.
```

### Cambiar número de preguntas
```python
self.max_questions = 10  # En EvaluatorAgent.__init__
```

### Cambiar voz TTS
Edita `backend/tts.py`:
```python
PIPER_VOICE = "es_MX-claude-high"  # Voces disponibles en huggingface.co/rhasspy/piper-voices
```

### Cambiar modelo Whisper
Edita `backend/stt.py`:
```python
WHISPER_MODEL = "medium"  # tiny | base | small | medium | large
```

---

## Estructura del proyecto

```
evaluador-agente/
├── backend/
│   ├── main.py         # FastAPI + WebSocket handler
│   ├── agent.py        # Lógica de evaluación + Ollama
│   ├── stt.py          # Whisper STT
│   ├── tts.py          # Piper TTS
│   └── requirements.txt
├── frontend/
│   └── index.html      # UI completa (sin dependencias)
├── proyectos/
│   └── gestion-tareas.md   # Ejemplo de proyecto
├── start.sh            # Setup + launch automático
└── README.md
```

---

## Reporte final

Al terminar la evaluación, el sistema genera un JSON con:
- Nombre del estudiante
- Fecha y duración
- Transcripción completa de la conversación
- Número de preguntas respondidas

El estudiante puede descargarlo desde la pantalla final.
El docente también puede revisar los reportes en tiempo real.
