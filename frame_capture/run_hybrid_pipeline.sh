#!/bin/bash

# --- Configuración ---
APP_TO_RUN="glxgears"
SHM_NAME="/dev/shm/shm_vgl_frame"
INTERCEPTOR="./wrapper_swapbuffers_shm.so"
WEBSERVER_SCRIPT="web_stream_gpu1.py"
GPU_FOR_STREAMING=1

# --- Paso 1: Compilar el interceptor ---
echo "[1/4] Compilando interceptor..."
./build.sh || { echo "❌ Error al compilar wrapper"; exit 1; }

# --- Paso 2: Iniciar aplicación OpenGL interceptada ---
echo "[2/4] Lanzando $APP_TO_RUN con LD_PRELOAD en GPU0..."
LD_PRELOAD=$INTERCEPTOR $APP_TO_RUN &
APP_PID=$!
sleep 2  # da tiempo a generar los primeros frames

# --- Paso 3: Lanzar servidor de lectura y streaming en GPU1 ---
echo "[3/4] Lanzando lector y superresolución en GPU${GPU_FOR_STREAMING}..."
CUDA_VISIBLE_DEVICES=$GPU_FOR_STREAMING python3 $WEBSERVER_SCRIPT &
SERVER_PID=$!

# --- Paso 4: Mostrar estado ---
echo "[4/4] Procesos lanzados:"
echo "🌀 App OpenGL ($APP_TO_RUN) PID: $APP_PID"
echo "🖥️  Web server Flask PID: $SERVER_PID"
echo "🌐 Accede al stream vía: http://localhost:5000/video_feed"
echo "📄 Memoria compartida usada: $SHM_NAME"

echo "✅ Todo lanzado. Pulsa Ctrl+C para detener manualmente."

# --- Mantener el script activo para que no se cierre ---
wait
