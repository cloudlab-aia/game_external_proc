#!/bin/bash

# Lista de resoluciones
RESOLUTIONS=(
  "128x72"
  "640x360"
  "1280x720"
  "1920x1080"
  "2560x1440"
)

# Ruta al script de benchmark (ajusta si necesario)
BENCHMARK_SCRIPT="benchmark_models.py"

# Tiempo máximo para abrir ventana
TIMEOUT_OPEN=5

# Función para extraer anchura y altura
parse_resolution() {
  WIDTH=$(echo $1 | cut -d'x' -f1)
  HEIGHT=$(echo $1 | cut -d'x' -f2)
}

for RES in "${RESOLUTIONS[@]}"; do
  echo "==============================="
  echo "Ejecutando benchmark para resolución $RES"
  echo "==============================="

  parse_resolution $RES

  # Ejecutar glxgears con LD_PRELOAD en segundo plano
  LD_PRELOAD=./libswapcapture.so glxgears & 
  GLX_PID=$!

  # Esperar a que se abra la ventana
  for i in $(seq 1 $TIMEOUT_OPEN); do
    if wmctrl -l | grep -i glxgears; then
      break
    fi
    sleep 1
  done

  # Cambiar tamaño de ventana
  wmctrl -r glxgears -e 0,100,100,$WIDTH,$HEIGHT
  echo "Ventana glxgears ajustada a ${WIDTH}x${HEIGHT}"

  # Ejecutar benchmark IA
  python3 $BENCHMARK_SCRIPT --input_size $WIDTH $HEIGHT --output_size 3840 2160 --device opencl --model fsrcnn_x2

  # Cerrar glxgears
  kill $GLX_PID
  sleep 1

done
