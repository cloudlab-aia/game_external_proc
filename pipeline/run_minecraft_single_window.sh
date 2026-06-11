#!/bin/bash
# Opción B — ventana única: el juego corre debajo (render en dGPU) y solo se
# ve el overlay fullscreen con el frame reescalado por IA (iGPU). El input va
# al juego (conserva foco de teclado y captura de puntero durante el juego).
#
# Cuanto más pequeña sea la ventana del juego, más trabajo ahorra la dGPU y
# más notable es el reescalado. Ajusta el tamaño en las opciones de vídeo de
# Minecraft (o deja el tamaño por defecto, 854x480).

LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
GAME_DISPLAY="${GAME_DISPLAY:-:1}"
SHM_PATH="/dev/shm/framebuffer_shared"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERCEPTOR="$REPO_DIR/capture/wrapper_swapbuffers_shm.so"
OVERLAY="$REPO_DIR/processing/display_overlay.py"
PYTHON="$REPO_DIR/venv/bin/python3"; [ -x "$PYTHON" ] || PYTHON="python3"

cleanup() { echo "Terminando..."; kill $LAUNCHER_PID $OVERLAY_PID 2>/dev/null; rm -f "$SHM_PATH"; }
trap cleanup EXIT INT TERM

[ -f "$INTERCEPTOR" ] || "$REPO_DIR/capture/build.sh" || exit 1
rm -f "$SHM_PATH"

echo "[1/2] Lanzando Minecraft (captura, solo proceso java)..."
env -u WAYLAND_DISPLAY DISPLAY="$GAME_DISPLAY" \
    LD_PRELOAD="$INTERCEPTOR" FRAME_CAPTURE_EXE=java \
    "$LAUNCHER" >/tmp/minecraft_launcher.log 2>&1 &
LAUNCHER_PID=$!

echo "[2/2] El overlay fullscreen arrancará en cuanto el juego genere frames."
echo "      Inicia sesión y dale a Jugar. Para salir: Ctrl+C aquí."

# Esperar a que el juego empiece a producir frames antes de cubrir la pantalla
echo -n "Esperando frames del juego"
while [ ! -f "$SHM_PATH" ]; do echo -n "."; sleep 1; done
echo " ¡listo!"

QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$GAME_DISPLAY" \
    GAME_WINDOW_NAME=Minecraft \
    "$PYTHON" "$OVERLAY" &
OVERLAY_PID=$!

wait $LAUNCHER_PID
