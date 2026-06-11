#!/bin/bash
# Pipeline completo con Minecraft: captura de frames del juego (dGPU NVIDIA)
# + superresolución en tiempo real (iGPU Intel, OpenVINO).
#
# Minecraft >= 1.13 usa LWJGL3/GLFW, que resuelve los símbolos GL mediante
# dlopen()/dlsym()/glXGetProcAddressARB(); el interceptor cubre también esas
# rutas. Se lanza sin WAYLAND_DISPLAY para forzar GLFW a X11 (XWayland) y
# que el juego use GLX, que es lo que interceptamos.

LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
GAME_DISPLAY="${GAME_DISPLAY:-:1}"     # display X (XWayland) con la dGPU
IGPU_MONITOR_X="${IGPU_MONITOR_X:-1920}" # offset X del monitor de la iGPU
SHM_PATH="/dev/shm/framebuffer_shared"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERCEPTOR="$REPO_DIR/capture/wrapper_swapbuffers_shm.so"
# Upscaler rápido (FSRCNN/OpenVINO, ~13 ms/frame ≈ 75 FPS). Para el modelo
# lento de mayor calidad usar UPSCALE_SCRIPT=processing/upscale_display.py
UPSCALE_SCRIPT="${UPSCALE_SCRIPT:-$REPO_DIR/processing/upscale_fsrcnn_ov.py}"

# Python del venv del proyecto si existe
PYTHON="$REPO_DIR/venv/bin/python3"
[ -x "$PYTHON" ] || PYTHON="python3"

cleanup() {
    echo "Terminando procesos..."
    kill $LAUNCHER_PID $UPSCALE_PID 2>/dev/null
    rm -f "$SHM_PATH"
}
trap cleanup EXIT INT TERM

# 1. Compilar interceptor si falta
[ -f "$INTERCEPTOR" ] || "$REPO_DIR/capture/build.sh" || exit 1

# 2. Limpiar shm de ejecuciones anteriores
rm -f "$SHM_PATH"

# 3. Lanzar el launcher de Minecraft con el interceptor
#    - sin WAYLAND_DISPLAY: GLFW cae a X11 → GLX → captura funciona
#    - LD_PRELOAD se hereda: launcher → JVM → juego
echo "[1/2] Lanzando Minecraft launcher con captura..."
# FRAME_CAPTURE_EXE=java: solo el proceso del juego (JVM) captura; el
# launcher hereda el wrapper pero queda inactivo (evita dos escritores
# simultáneos en la shm, que provocaba SIGBUS en el juego).
env -u WAYLAND_DISPLAY DISPLAY="$GAME_DISPLAY" \
    LD_PRELOAD="$INTERCEPTOR" FRAME_CAPTURE_EXE=java \
    "$LAUNCHER" >/tmp/minecraft_launcher.log 2>&1 &
LAUNCHER_PID=$!

# 4. Lanzar superresolución (espera sola a que aparezcan frames en la shm)
echo "[2/2] Lanzando superresolución OpenVINO (iGPU)..."
# QT_QPA_PLATFORM=xcb: en sesión Wayland, el Qt de OpenCV no trae plugin
# Wayland y la ventana saldría negra; forzar X11.
QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$GAME_DISPLAY" \
    IGPU_MONITOR_X="$IGPU_MONITOR_X" \
    "$PYTHON" "$UPSCALE_SCRIPT" &
UPSCALE_PID=$!

echo ""
echo "Launcher PID: $LAUNCHER_PID  (log: /tmp/minecraft_launcher.log)"
echo "Upscaler PID: $UPSCALE_PID"
echo ""
echo "Inicia sesión y arranca el juego. Cuando Minecraft abra su ventana,"
echo "los frames aparecerán en $SHM_PATH y la ventana de IA empezará a"
echo "mostrar el juego reescalado. 'q' en la ventana de IA o Ctrl+C aquí"
echo "para parar todo."

wait $LAUNCHER_PID
