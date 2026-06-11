#!/bin/bash

# Script para ejecutar el pipeline completo de AI upscaling
# Captura frames de OpenGL y los procesa con IA en tiempo real

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
WRAPPER_LIB="$REPO_DIR/capture/libswapcapture.so"
PYTHON_SCRIPT="$REPO_DIR/processing/upscale_openvino.py"
SHM_NAME="/dev/shm/framebuffer_shared"

echo "=== AI Game External Processing Pipeline ==="
echo "Directorio: $SCRIPT_DIR"
echo "Wrapper: $WRAPPER_LIB"
echo "Script IA: $PYTHON_SCRIPT"

# Función para limpiar al salir
cleanup() {
    echo "Limpiando..."
    # Eliminar memoria compartida si existe
    if [ -f "$SHM_NAME" ]; then
        rm -f "$SHM_NAME"
        echo "Memoria compartida eliminada"
    fi
    
    # Matar procesos hijos
    jobs -p | xargs -r kill
    echo "Procesos terminados"
}

# Configurar trap para limpiar al salir
trap cleanup EXIT INT TERM

# Verificar que el wrapper existe
if [ ! -f "$WRAPPER_LIB" ]; then
    echo "Error: No se encuentra el wrapper $WRAPPER_LIB"
    echo "Ejecuta: capture/build.sh"
    exit 1
fi

# Verificar que el script de Python existe
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: No se encuentra el script de Python $PYTHON_SCRIPT"
    exit 1
fi

# Verificar que el modelo existe
MODEL_XML="/home/ogg/Desktop/AIA/game_external_proc/models/single-image-super-resolution-1032.xml"
if [ ! -f "$MODEL_XML" ]; then
    echo "Error: No se encuentra el modelo $MODEL_XML"
    exit 1
fi

echo "Todos los archivos necesarios encontrados"

# Función para mostrar ayuda
show_help() {
    echo ""
    echo "Uso:"
    echo "  $0 [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  glxgears    - Ejecutar glxgears con captura de IA"
    echo "  supertux    - Ejecutar SuperTuxKart con captura de IA" 
    echo "  custom CMD  - Ejecutar comando personalizado con captura"
    echo "  test        - Solo ejecutar el procesamiento de IA (sin juego)"
    echo ""
    echo "Ejemplos:"
    echo "  $0 glxgears"
    echo "  $0 custom 'glxspheres -geometry 1920x1080'"
    echo "  $0 test"
}

# Función para ejecutar el procesamiento de IA
start_ai_processing() {
    echo "Iniciando procesamiento de IA..."
    python3 "$PYTHON_SCRIPT" &
    AI_PID=$!
    echo "Procesamiento de IA iniciado (PID: $AI_PID)"
}

# Función para ejecutar juego con wrapper
run_with_wrapper() {
    local cmd="$1"
    echo "Ejecutando: $cmd"
    echo "Con wrapper: $WRAPPER_LIB"
    
    # Configurar LD_PRELOAD y ejecutar
    export LD_PRELOAD="$WRAPPER_LIB"
    eval "$cmd"
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

case "$1" in
    "glxgears")
        echo "Modo: GLX Gears con AI upscaling"
        python3 "$PYTHON_SCRIPT" &
        AI_PID=$!
        sleep 2
        LD_PRELOAD="$WRAPPER_LIB" glxgears
        wait $AI_PID
        ;;
        
    "supertux")
        echo "Modo: SuperTuxKart con AI upscaling"
        if ! command -v supertuxkart &> /dev/null; then
            echo "Error: SuperTuxKart no está instalado"
            echo "Instala con: sudo apt install supertuxkart"
            exit 1
        fi
        start_ai_processing
        sleep 2
        run_with_wrapper "supertuxkart --screensize=1920x1080 --fullscreen=false"
        ;;
        
    "custom")
        if [ $# -lt 2 ]; then
            echo "Error: Falta el comando personalizado"
            echo "Uso: $0 custom 'tu_comando_aqui'"
            exit 1
        fi
        echo "Modo: Comando personalizado con AI upscaling"
        start_ai_processing
        sleep 2
        run_with_wrapper "$2"
        ;;
        
    "test")
        echo "Modo: Solo procesamiento de IA (sin juego)"
        echo "Ejecuta en otra terminal un juego OpenGL para ver el resultado"
        python3 "$PYTHON_SCRIPT"
        ;;
        
    "help"|"-h"|"--help")
        show_help
        ;;
        
    *)
        echo "Error: Comando desconocido '$1'"
        show_help
        exit 1
        ;;
esac

echo "Pipeline completado"