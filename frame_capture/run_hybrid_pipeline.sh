#!/bin/bash

# --- Configuración ---
APP_TO_RUN="glxgears -info"
# El nombre debe coincidir exactamente con el del wrapper C y el script Python
SHM_NAME="/framebuffer_shared"
INTERCEPTOR="$(pwd)/wrapper_swapbuffers_shm.so"
WEBSERVER_SCRIPT="web_stream_gpu1.py"
GPU_FOR_STREAMING=1
VIRTUAL_DISPLAY=":1"

# --- Limpieza al salir ---
# Se define el trap al principio para que capture la salida en cualquier punto
# Se elimina 'sudo' ya que no está disponible en el contenedor
trap "echo 'Terminando procesos...'; kill $APP_PID $SERVER_PID $XVFB_PID 2>/dev/null; rm -f /dev/shm$SHM_NAME; exit" SIGINT SIGTERM

# --- Paso 1: Compilar el interceptor ---
echo "[1/4] Compilando interceptor..."
./build.sh || { echo "❌ Error al compilar wrapper"; exit 1; }

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

# --- Paso 4: Lanzar servidor de lectura y streaming en GPU1 ---
echo "[4/4] Lanzando lector y superresolución en GPU${GPU_FOR_STREAMING}..."
# Hacemos el script de python ejecutable y lo lanzamos directamente para evitar problemas de permisos
chmod +x $WEBSERVER_SCRIPT
CUDA_VISIBLE_DEVICES=$GPU_FOR_STREAMING ./$WEBSERVER_SCRIPT &
SERVER_PID=$!

# --- Paso 5: Mostrar estado ---
echo "[5/5] Procesos lanzados:"
echo "🖥️  Servidor X virtual (Xvfb) PID: $XVFB_PID"
echo "🌀 App OpenGL ($APP_TO_RUN) PID: $APP_PID"
echo "🐍 Web server Flask PID: $SERVER_PID"
echo "🌐 Accede al stream vía: http://<IP_DEL_SERVIDOR>:5000/video_feed"
echo "📄 Memoria compartida usada: $SHM_NAME"

echo "✅ Todo lanzado. Pulsa Ctrl+C para detener."

# Mantener el script activo
wait
