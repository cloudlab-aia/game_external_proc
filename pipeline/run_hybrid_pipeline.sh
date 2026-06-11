#!/bin/bash

# --- Configuración ---
APP_TO_RUN="glxgears -geometry 1920x1080"  # Debe coincidir con WIDTH/HEIGHT del wrapper C
# El nombre debe coincidir exactamente con el del wrapper C y el script Python
SHM_NAME="/framebuffer_shared"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERCEPTOR="$REPO_DIR/capture/wrapper_swapbuffers_shm.so"
UPSCALE_SCRIPT="$REPO_DIR/processing/upscale_display.py"
VIRTUAL_DISPLAY=":2"          # Display virtual donde corre el juego (dGPU) — :1 ya lo usa tu sesión
REAL_DISPLAY=":1"             # Display real de tu sesión X con los monitores físicos
# El monitor de la iGPU (HDMI-A-3) empieza en X=1920 en tu configuración de pantalla dual
IGPU_MONITOR_X=1920           # Posición horizontal del monitor iGPU para mover la ventana ahí
# Exportar XAUTHORITY para que el script Python pueda abrir ventanas en :0
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# --- Limpieza al salir ---
trap "echo 'Terminando procesos...'; kill \$APP_PID \$UPSCALE_PID \$XVFB_PID 2>/dev/null; rm -f /dev/shm$SHM_NAME; exit" SIGINT SIGTERM

# --- Paso 1: Compilar el interceptor ---
echo "[1/4] Compilando interceptor..."
"$REPO_DIR/capture/build.sh" || { echo "❌ Error al compilar wrapper"; exit 1; }

# --- Paso 2: Iniciar el servidor X virtual (Xvfb) ---
echo "[2/4] Lanzando servidor X virtual (Xvfb) en el display $VIRTUAL_DISPLAY..."
Xvfb $VIRTUAL_DISPLAY -screen 0 1920x1080x24 &
XVFB_PID=$!
sleep 2 # Dar tiempo a que Xvfb se inicie

# --- Paso 3: Iniciar aplicación OpenGL interceptada ---
echo "[3/4] Lanzando $APP_TO_RUN con LD_PRELOAD en el display virtual..."
DISPLAY=$VIRTUAL_DISPLAY LD_PRELOAD=$INTERCEPTOR $APP_TO_RUN &
APP_PID=$!
sleep 3 # da más tiempo para que el wrapper cree la memoria compartida

# --- Paso 4: Lanzar upscaling IA → salida en monitor iGPU ---
echo "[4/4] Lanzando upscaling IA (OpenVINO iGPU) → ventana en monitor $REAL_DISPLAY..."
# DISPLAY=:0  → la ventana cv2.imshow() aparece en el monitor físico de la iGPU
# CUDA_VISIBLE_DEVICES="" → ocultar dGPU NVIDIA a OpenCV/OpenVINO (usan iGPU Intel)
QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY=$REAL_DISPLAY IGPU_MONITOR_X=$IGPU_MONITOR_X python3 $UPSCALE_SCRIPT &
UPSCALE_PID=$!

# --- Paso 5: Mostrar estado ---
echo ""
echo "[5/5] Procesos lanzados:"
echo "🖥️  Servidor X virtual (Xvfb) PID: $XVFB_PID  → DISPLAY=$VIRTUAL_DISPLAY"
echo "🎮 App OpenGL ($APP_TO_RUN) PID: $APP_PID  → renderiza en dGPU"
echo "🤖 Upscaling IA (OpenVINO) PID: $UPSCALE_PID  → ventana en $REAL_DISPLAY (iGPU)"
echo "📄 Memoria compartida: /dev/shm$SHM_NAME"
echo ""
echo "✅ Todo lanzado. Pulsa 'q' en la ventana de IA o Ctrl+C aquí para detener."

# Mantener el script activo
wait
