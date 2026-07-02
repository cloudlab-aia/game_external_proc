#!/bin/bash
# Barrido de FPS de render REAL del juego por resolución.
# Redimensiona la ventana del juego (en la pantalla virtual :2) a cada
# resolución, deja asentar y mide el FPS de render (contador del buzón shm).
#
# REQUISITOS: juego corriendo y capturándose en :2. Quédate QUIETO toda la
# medida (el movimiento/carga de chunks falsea el FPS).
#
# Uso:  experiments/run_fps_sweep.sh [segundos_por_resolucion] [display]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/fps_resolution_sweep.csv"
DISP="${2:-:2}"
SECS="${1:-8}"

[ -f "$SHM" ] || { echo "No hay captura ($SHM). ¿Juego corriendo en $DISP?"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && GW=$(DISPLAY=$DISP xdotool search --class minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "No encuentro la ventana del juego en $DISP"; exit 1; }
echo "Ventana del juego: $GW en $DISP"
echo "resolucion_objetivo,resolucion_real,fps_render" > "$OUT"

for RES in 426x240 480x270 640x360 854x480 960x540 1280x720; do
  W=${RES%x*}; H=${RES#*x}
  DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H" 2>/dev/null
  # asentar: esperar a que el shm refleje la nueva resolución (python, no sleep de shell)
  $PY -c "
import struct,time
for _ in range(50):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$W)<=4 and abs(h-$H)<=4: break
    time.sleep(0.1)
time.sleep(1.5)"
  REAL=$($PY -c "import struct;w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16));print(f'{w}x{h}')")
  FPS=$($PY benchmarks/render_fps.py --seconds "$SECS" --interval "$SECS" 2>/dev/null | grep "de media" | grep -oE "[0-9]+\.[0-9]+" | head -1)
  echo "  $RES (real $REAL): ${FPS} FPS"
  echo "$RES,$REAL,$FPS" >> "$OUT"
done

echo ""
echo "=== Barrido FPS de render por resolución ==="
column -t -s, "$OUT"
