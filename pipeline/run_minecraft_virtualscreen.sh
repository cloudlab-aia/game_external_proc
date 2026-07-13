#!/bin/bash
# Pantalla virtual SOLO para el juego, el launcher se usa con normalidad.
#
# El launcher de Minecraft se abre normal en el display real. Un interceptor
# (capture/game_launch_interposer.so) vigila qué procesos lanza el launcher y,
# SOLO cuando arranca el juego (la JVM con "net.minecraft"), lo redirige a una
# pantalla virtual oculta (Xvfb) renderizada por la dGPU vía VirtualGL, y
# captura sus frames. El overlay muestra el juego reescalado por IA (iGPU) en
# una ventana real y te reenvía teclado/ratón al juego.
#
#   launcher (normal, :1)
#     └─[interceptor]─> juego (Xvfb :2, VirtualGL→dGPU, captura a shm)
#                          └─> iGPU FSRCNN ─> overlay en :1 (+ reenvío input)

LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
VIRT_DISPLAY="${VIRT_DISPLAY:-:2}"
GPU_DISPLAY="${GPU_DISPLAY:-:1}"
REAL_DISPLAY="${REAL_DISPLAY:-:1}"
VIRT_RES="${VIRT_RES:-1280x720x24}"
SHM_PATH="/dev/shm/framebuffer_shared"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VGLLIB="$REPO_DIR/virtualgl/build/lib"
INTERPOSER="$REPO_DIR/capture/game_launch_interposer.so"
OVERLAY="$REPO_DIR/processing/display_overlay_forward.py"
PYTHON="$REPO_DIR/venv/bin/python3"; [ -x "$PYTHON" ] || PYTHON="python3"

TJPEG_DIR="$HOME/.local/vgldeps"
VGL_LDPATH="$VGLLIB:$TJPEG_DIR:/tmp/tjpeg/usr/lib/x86_64-linux-gnu"
VGL_PRELOAD="$VGLLIB/libdlfaker.so:$VGLLIB/libvglfaker.so"

cleanup() { echo "Terminando..."; kill $LAUNCHER_PID $OVERLAY_PID $XVFB_PID 2>/dev/null; rm -f "$SHM_PATH"; }
trap cleanup EXIT INT TERM

[ -f "$VGLLIB/libvglfaker.so" ] || { echo "Falta VirtualGL en $VGLLIB"; exit 1; }
[ -f "$INTERPOSER" ] || gcc -shared -fPIC -O2 -o "$INTERPOSER" "$REPO_DIR/capture/game_launch_interposer.c" -ldl || exit 1
rm -f "$SHM_PATH"

echo "[1/3] Pantalla virtual oculta Xvfb en $VIRT_DISPLAY ($VIRT_RES)..."
Xvfb "$VIRT_DISPLAY" -screen 0 "$VIRT_RES" >/tmp/xvfb_virtualscreen.log 2>&1 &
XVFB_PID=$!

echo "[2/3] Abriendo el launcher NORMAL en $REAL_DISPLAY (el juego irá a $VIRT_DISPLAY)..."
# El launcher corre normal; el interceptor solo redirige el proceso del juego.
# Esas GAME_* las lee el interceptor para reescribir el entorno del juego.
DISPLAY="$REAL_DISPLAY" \
  LD_PRELOAD="$INTERPOSER" \
  GAME_VIRT_DISPLAY="$VIRT_DISPLAY" \
  GAME_VGL_DISPLAY="$GPU_DISPLAY" \
  GAME_VGL_PRELOAD="$VGL_PRELOAD" \
  GAME_VGL_LDPATH="$VGL_LDPATH" \
  "$LAUNCHER" >/tmp/minecraft_launcher.log 2>&1 &
LAUNCHER_PID=$!

echo "[3/3] Inicia sesión y dale a Jugar con normalidad."
echo "      Al abrir el juego empezará la captura y aparecerá el overlay IA."
echo -n "Esperando a que arranque el juego"
for i in $(seq 1 600); do [ -f "$SHM_PATH" ] && break; printf '.'; sleep 1; done
echo
[ -f "$SHM_PATH" ] || { echo "El juego no generó frames; revisa /tmp/minecraft_launcher.log"; exit 1; }

# Overlay: muestra el juego (oculto en :2) reescalado y reenvía input a :2.
QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$REAL_DISPLAY" \
    TARGET_DISPLAY="$VIRT_DISPLAY" \
    "$PYTHON" "$OVERLAY" &
OVERLAY_PID=$!

echo ""
echo "Juego en pantalla virtual $VIRT_DISPLAY (oculta, render dGPU). Ves el overlay IA."
echo "Tu teclado/ratón se reenvían al juego. Salir: F12 en el overlay, o Ctrl+C aquí."
wait $OVERLAY_PID
