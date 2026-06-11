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
# Resolución de render del juego: pequeña = la dGPU renderiza pocos píxeles
# (rápido) y la IA reconstruye 1080p. 480x270 coincide con la entrada de
# FSRCNN x4 → reconstrucción pura sin reescalado previo.
GAME_W="${GAME_W:-480}"
GAME_H="${GAME_H:-270}"
GRAB_SECONDS="${GRAB_SECONDS:-12}"

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

# Encoger la ventana del juego a baja resolución (la dGPU renderiza pocos
# píxeles) y centrarla, visible, para que puedas capturar el puntero.
GW=$(DISPLAY="$GAME_DISPLAY" xdotool search --name Minecraft 2>/dev/null | tail -1)
if [ -n "$GW" ]; then
    SW=$(DISPLAY="$GAME_DISPLAY" xdotool getdisplaygeometry | cut -d' ' -f1)
    SH=$(DISPLAY="$GAME_DISPLAY" xdotool getdisplaygeometry | cut -d' ' -f2)
    PX=$(( (SW - GAME_W) / 2 )); PY=$(( (SH - GAME_H) / 2 ))
    DISPLAY="$GAME_DISPLAY" xdotool windowsize "$GW" "$GAME_W" "$GAME_H" \
        windowmove "$GW" "$PX" "$PY" windowactivate "$GW" 2>/dev/null
fi

echo ""
echo ">>> El juego corre a ${GAME_W}x${GAME_H} (render pésimo en la dGPU)."
echo ">>> HAZ CLIC en la ventanita del juego y empieza a jugar (captura el ratón)."
echo ">>> En $GRAB_SECONDS s el overlay cubrirá la pantalla con la versión IA a 1080p."
for ((i=GRAB_SECONDS; i>0; i--)); do echo -n "$i "; sleep 1; done; echo

QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$GAME_DISPLAY" \
    GAME_WINDOW_NAME=Minecraft \
    "$PYTHON" "$OVERLAY" &
OVERLAY_PID=$!

wait $LAUNCHER_PID
