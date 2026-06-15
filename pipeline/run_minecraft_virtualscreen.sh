#!/bin/bash
# Opción A — Pantalla virtual real: el juego corre en una pantalla X virtual
# (Xvfb, oculta) PERO el render 3D lo hace la dGPU NVIDIA gracias a VirtualGL.
# Solo se ve el overlay fullscreen con la salida reescalada por IA (iGPU).
#
# Cumple el requisito del enunciado: la imagen generada por la dGPU no se
# muestra directamente; corre en pantalla virtual y solo se presenta el
# resultado procesado.
#
# Arquitectura:
#   Xvfb :2 (pantalla virtual, oculta)
#     + VirtualGL → render 3D en la dGPU NVIDIA (VGL_DISPLAY=:1)
#     + hook hybridCaptureToShm → frame a /dev/shm/framebuffer_shared
#   processing/display_overlay.py (iGPU OpenVINO FSRCNN) → overlay en :1

LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
VIRT_DISPLAY="${VIRT_DISPLAY:-:2}"   # pantalla virtual (oculta)
GPU_DISPLAY="${GPU_DISPLAY:-:1}"     # display con la dGPU NVIDIA (render VGL)
REAL_DISPLAY="${REAL_DISPLAY:-:1}"   # donde se ve el overlay
VIRT_RES="${VIRT_RES:-1280x720x24}"
SHM_PATH="/dev/shm/framebuffer_shared"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VGLLIB="$REPO_DIR/virtualgl/build/lib"
OVERLAY="$REPO_DIR/processing/display_overlay.py"
PYTHON="$REPO_DIR/venv/bin/python3"; [ -x "$PYTHON" ] || PYTHON="python3"

# Dependencia de runtime de VGL (turbojpeg) en ubicación estable
TJPEG_DIR="$HOME/.local/vgldeps"
VGL_LD="$VGLLIB:$TJPEG_DIR:/tmp/tjpeg/usr/lib/x86_64-linux-gnu"

cleanup() { echo "Terminando..."; kill $LAUNCHER_PID $OVERLAY_PID $XVFB_PID 2>/dev/null; rm -f "$SHM_PATH"; }
trap cleanup EXIT INT TERM

[ -f "$VGLLIB/libvglfaker.so" ] || { echo "Falta VirtualGL compilado en $VGLLIB"; exit 1; }
rm -f "$SHM_PATH"

echo "[1/3] Pantalla virtual Xvfb en $VIRT_DISPLAY ($VIRT_RES)..."
Xvfb "$VIRT_DISPLAY" -screen 0 "$VIRT_RES" >/tmp/xvfb_virtualscreen.log 2>&1 &
XVFB_PID=$!
sleep 2

echo "[2/3] Lanzando Minecraft en la pantalla virtual (render dGPU vía VirtualGL)..."
# DISPLAY=:2  → ventana del juego en la pantalla virtual (oculta)
# VGL_DISPLAY=:1 → VirtualGL hace el render 3D en la dGPU NVIDIA
# FRAME_CAPTURE_EXE no aplica aquí: la captura la hace el hook de VGL
env -u WAYLAND_DISPLAY DISPLAY="$VIRT_DISPLAY" VGL_DISPLAY="$GPU_DISPLAY" \
    LD_LIBRARY_PATH="$VGL_LD" \
    LD_PRELOAD="$VGLLIB/libdlfaker.so:$VGLLIB/libvglfaker.so" \
    vblank_mode=0 \
    "$LAUNCHER" >/tmp/minecraft_virtualscreen.log 2>&1 &
LAUNCHER_PID=$!

echo "[3/3] Esperando frames del juego para arrancar el overlay IA..."
echo -n "Esperando"
for i in $(seq 1 120); do [ -f "$SHM_PATH" ] && break; echo -n "."; sleep 1; done; echo
[ -f "$SHM_PATH" ] || { echo "No llegaron frames; revisa /tmp/minecraft_virtualscreen.log"; exit 1; }

QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$REAL_DISPLAY" \
    "$PYTHON" "$OVERLAY" &
OVERLAY_PID=$!

echo ""
echo "Minecraft corre en pantalla virtual $VIRT_DISPLAY (no se ve)."
echo "Solo ves el overlay IA. Inicia sesión y juega. Ctrl+C aquí para salir."
wait $LAUNCHER_PID
