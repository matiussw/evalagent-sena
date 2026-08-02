#!/bin/bash
# ════════════════════════════════════════════════════════
#  EvalAgent SENA — Setup & Run Script
#  Compatible: macOS (M1/M4) | Ubuntu/Debian
# ════════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[eval-agent]${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }

echo ""
echo "════════════════════════════════════════"
echo "  EvalAgent SENA — Setup & Launch"
echo "════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$SCRIPT_DIR/.venv"

# ─── 1. Check dependencies ───────────────────────────
log "Verificando dependencias..."

# Python 3.10+
if ! command -v python3 &>/dev/null; then
  err "Python 3 no encontrado. Instálalo con: brew install python3"
  exit 1
fi
ok "Python 3: $(python3 --version)"

# ffmpeg (required for audio conversion)
if ! command -v ffmpeg &>/dev/null; then
  warn "ffmpeg no encontrado. Instalando..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ffmpeg
  else
    sudo apt-get install -y ffmpeg
  fi
fi
ok "ffmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"

# Ollama
if ! command -v ollama &>/dev/null; then
  warn "Ollama no encontrado."
  echo "  Instala desde: https://ollama.com/download"
  echo "  Luego ejecuta: ollama pull llama3.1:8b"
  exit 1
fi
ok "Ollama: instalado"

# Check if model is available
if ollama list 2>/dev/null | grep -q "llama3.1:8b"; then
  ok "Modelo llama3.1:8b: disponible"
else
  warn "Descargando modelo llama3.1:8b (esto puede tardar ~5GB)..."
  ollama pull llama3.1:8b
fi

# ─── 2. Python venv ──────────────────────────────────
log "Configurando entorno Python..."

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  ok "Virtualenv creado en .venv/"
fi

source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q --only-binary=:all: av
pip install -q -r "$BACKEND_DIR/requirements.txt"
ok "Dependencias Python instaladas"

# ─── 3. Piper TTS ────────────────────────────────────
log "Configurando Piper TTS..."

PIPER_DIR="$HOME/.local/share/piper-voices"
PIPER_BIN="$HOME/.local/bin/piper"

mkdir -p "$PIPER_DIR" "$HOME/.local/bin"

if [ ! -f "$PIPER_BIN" ]; then
  warn "Piper no encontrado. Descargando..."
  
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if [[ $(uname -m) == "arm64" ]]; then
      PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_aarch64.tar.gz"
    else
      PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_x64.tar.gz"
    fi
  else
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
  fi

  TMP=$(mktemp -d)
  curl -L -o "$TMP/piper.tar.gz" "$PIPER_URL"
  tar -xzf "$TMP/piper.tar.gz" -C "$TMP"
  cp "$TMP/piper/piper" "$PIPER_BIN"
  chmod +x "$PIPER_BIN"
  rm -rf "$TMP"
  ok "Piper instalado"
fi

# Download Spanish voice model
VOICE_ONNX="$PIPER_DIR/es_ES-davefx-medium.onnx"
VOICE_JSON="$PIPER_DIR/es_ES-davefx-medium.onnx.json"

if [ ! -f "$VOICE_ONNX" ]; then
  warn "Descargando voz en español (es_ES-davefx-medium)..."
  BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium"
  curl -L -o "$VOICE_ONNX" "$BASE/es_ES-davefx-medium.onnx"
  curl -L -o "$VOICE_JSON" "$BASE/es_ES-davefx-medium.onnx.json"
  ok "Voz española descargada"
fi
ok "Piper TTS: listo"

# ─── 4. Launch ───────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
ok "Todo listo. Iniciando EvalAgent..."
echo ""
log "Backend:  http://localhost:8000"
log "Exposición local: accesible en tu red con ngrok o cloudflare tunnel"
echo ""
echo "  Para exponer con ngrok:          ngrok http 8000"
echo "  Para exponer con Cloudflare:     cloudflared tunnel --url http://localhost:8000"
echo ""
echo "  Ctrl+C para detener"
echo "════════════════════════════════════════"
echo ""

cd "$BACKEND_DIR"
source "$VENV_DIR/bin/activate"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
