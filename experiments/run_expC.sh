#!/bin/bash
# Exp C, FPS del JUEGO con shaders: nativa vs dedicada (IA en dGPU) vs híbrida
# (IA en iGPU). Mide el FPS de render del juego (contador del buzón) en tres
# condiciones, a la resolución de ventana ACTUAL del juego.
#
# REQUISITOS antes de lanzar:
#   - Minecraft con shaders corriendo y CAPTURÁNDOSE (run_minecraft_single_window.sh
#     o run_minecraft_virtualscreen_prime.sh). El juego debe estar produciendo frames.
#   - Plántate quieto en una escena exigente (no te muevas durante la medida).
#
# Protocolo recomendado:
#   1. Ventana del juego a 1920x1080 → ejecuta este script  → fila "nativa/dedicada".
#   2. Ventana del juego a baja res (p.ej. 960x540) → ejecuta de nuevo → fila "híbrida".
#   (la híbrida renderiza bajo y la iGPU reconstruye; la nativa renderiza alto)
#
# Uso:  experiments/run_expC.sh [segundos_por_fase]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SECS="${1:-15}"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/expC_shaders.csv"

[ -f "$SHM" ] || { echo "No hay captura. ¿Está el juego corriendo y capturándose?"; exit 1; }
RES=$($PY -c "import struct;d=open('$SHM','rb').read(16);w,h,_,_=struct.unpack('IIII',d);print(f'{w}x{h}')")
echo "Resolución de render actual: $RES"
[ -f "$OUT" ] || echo "config,resolucion,fps_render" > "$OUT"

measure() {  # $1 = etiqueta
  echo "--- midiendo [$1] durante ${SECS}s (no te muevas) ---"
  fps=$($PY benchmarks/render_fps.py --seconds "$SECS" --interval 5 2>/dev/null | grep "de media" | grep -oE "[0-9]+\.[0-9]+ FPS" | head -1 | grep -oE "[0-9]+\.[0-9]+")
  echo "  [$1] $RES -> ${fps} FPS"
  echo "$1,$RES,$fps" >> "$OUT"
}

# 1. Sin IA (coste de render puro a esta resolución)
measure "sin_IA"

# 2. IA en dGPU (dedicada: compite con el render del juego)
$PY experiments/upscale_consumer.py --device dGPU --scale 4 >/tmp/cons_dgpu.log 2>&1 &
CPID=$!; sleep 3
measure "IA_dGPU_dedicada"
kill $CPID 2>/dev/null; wait $CPID 2>/dev/null; sleep 2

# 3. IA en iGPU (híbrida: no toca la dGPU)
$PY experiments/upscale_consumer.py --device iGPU --scale 4 >/tmp/cons_igpu.log 2>&1 &
CPID=$!; sleep 3
measure "IA_iGPU_hibrida"
kill $CPID 2>/dev/null; wait $CPID 2>/dev/null

echo ""
echo "=== Exp C a $RES ==="
column -t -s, "$OUT"
echo ""
echo "Interpretación: a 1080p, IA_dGPU baja el FPS (roba render), IA_iGPU no."
echo "Repite con la ventana del juego a baja resolución para la fila híbrida."
