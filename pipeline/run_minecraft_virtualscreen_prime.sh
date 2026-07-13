#!/bin/bash
# Pantalla virtual SOLO para el juego, vía PRIME render offload (SIN VirtualGL).
#
# El juego corre en una pantalla virtual oculta (Xvfb), pero el render 3D lo
# hace la dGPU NVIDIA de forma NATIVA mediante PRIME render offload
# (__NV_PRIME_RENDER_OFFLOAD + __GLX_VENDOR_LIBRARY_NAME=nvidia). Sin la capa
# de VirtualGL → sin su incompatibilidad con motores GL modernos → permite
# Minecraft moderno (1.20/1.21) y shaders. La captura usa el interceptor propio
# (más rápido que el hook de VGL). No necesita root.
#
#   launcher normal (:1)
#     └─[game_launch_interposer]─> juego en Xvfb :2 con PRIME (render dGPU)
#          + wrapper_swapbuffers_shm.so captura → shm
#            └─> iGPU FSRCNN ─> display_overlay_forward.py en :1 (+ input → :2)
#
# Alternativa a run_minecraft_virtualscreen.sh (vía VirtualGL, solo GL clásico).

LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
VIRT_DISPLAY="${VIRT_DISPLAY:-:2}"
REAL_DISPLAY="${REAL_DISPLAY:-:1}"
VIRT_RES="${VIRT_RES:-1280x720x24}"
SHM_PATH="/dev/shm/framebuffer_shared"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERPOSER="$REPO_DIR/capture/game_launch_interposer.so"
WRAPPER="$REPO_DIR/capture/wrapper_swapbuffers_shm.so"
OVERLAY="$REPO_DIR/processing/display_overlay_forward.py"
PYTHON="$REPO_DIR/venv/bin/python3"; [ -x "$PYTHON" ] || PYTHON="python3"

cleanup() { echo "Terminando..."; kill $LAUNCHER_PID $OVERLAY_PID $XVFB_PID 2>/dev/null; rm -f "$SHM_PATH"; }
trap cleanup EXIT INT TERM

[ -f "$INTERPOSER" ] || gcc -shared -fPIC -O2 -o "$INTERPOSER" "$REPO_DIR/capture/game_launch_interposer.c" -ldl || exit 1
[ -f "$WRAPPER" ] || "$REPO_DIR/capture/build.sh" || exit 1
rm -f "$SHM_PATH"

echo "[1/3] Pantalla virtual oculta Xvfb en $VIRT_DISPLAY ($VIRT_RES)..."
Xvfb "$VIRT_DISPLAY" -screen 0 "$VIRT_RES" >/tmp/xvfb_virtualscreen.log 2>&1 &
XVFB_PID=$!
sleep 2

echo "[2/3] Abriendo el launcher NORMAL en $REAL_DISPLAY (el juego irá a $VIRT_DISPLAY con PRIME)..."
# El interceptor manda SOLO el proceso del juego a la pantalla virtual con
# PRIME (render NVIDIA nativo) + el wrapper de captura.
DISPLAY="$REAL_DISPLAY" \
  LD_PRELOAD="$INTERPOSER" \
  GAME_VIRT_DISPLAY="$VIRT_DISPLAY" \
  GAME_VGL_PRELOAD="$WRAPPER" \
  GAME_EXTRA_ENV="__NV_PRIME_RENDER_OFFLOAD=1;__GLX_VENDOR_LIBRARY_NAME=nvidia" \
  "$LAUNCHER" >/tmp/minecraft_launcher.log 2>&1 &
LAUNCHER_PID=$!

echo "[3/3] Inicia sesión y dale a Jugar. Al abrir el juego empezará la captura."
echo -n "Esperando a que arranque el juego"
for i in $(seq 1 600); do [ -f "$SHM_PATH" ] && break; printf '.'; sleep 1; done
echo
[ -f "$SHM_PATH" ] || { echo "El juego no generó frames; revisa /tmp/minecraft_launcher.log"; exit 1; }

QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$REAL_DISPLAY" \
    TARGET_DISPLAY="$VIRT_DISPLAY" \
    "$PYTHON" "$OVERLAY" &
OVERLAY_PID=$!

echo ""
echo "Juego en pantalla virtual $VIRT_DISPLAY (oculta, render dGPU vía PRIME, sin VirtualGL)."
echo "Ves el overlay IA; tu teclado/ratón se reenvían al juego. Salir: F12 o Ctrl+C."
wait $OVERLAY_PID
