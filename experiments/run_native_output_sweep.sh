#!/bin/bash
# Barrido NATIVO por resolucion de salida: FPS del juego renderizando
# directamente a cada resolucion de salida del Exp G, sin sistema de
# super-resolucion (sin consumidor). Sirve para anadir la recta "nativa a la
# resolucion de salida" a las graficas hibrida vs dedicada del Exp G.
#
# Resoluciones = salidas de los 15 puntos del Exp G (entrada x escala):
#   x2: 640x360 960x540 1280x720 1708x960 1920x1080
#   x3: 960x540 1440x810 1920x1080 2562x1440 2880x1620
#   x4: 1280x720 1920x1080 2560x1440 3416x1920 3840x2160
#
# REQUISITOS: juego en vivo capturandose en la pantalla virtual con
# CAPTURE_SKIP_PRESENT=1, en un mundo, quieto, SIN consumidor ni overlay
# (lanzar pipeline/run_arquitectura_final.sh con VIRT_RES=3840x2160x24 y
# KEEP_GAME=1, posicionarse y cerrar el overlay con F12).
#
# Uso: experiments/run_native_output_sweep.sh [display] [seg_medida]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/expG_native_output.csv"
DISP="${1:-:2}"; M="${2:-8}"

RESOLUTIONS="640x360 960x540 1280x720 1440x810 1708x960 1920x1080 2560x1440 2562x1440 2880x1620 3416x1920 3840x2160"

[ -f "$SHM" ] || { echo "No hay captura. ¿Juego en $DISP?"; exit 1; }
if pgrep -f "upscale_consumer|display_overlay_forward" >/dev/null; then
    echo "ERROR: hay un consumidor u overlay activo. Cierralo para medir en nativo."
    exit 1
fi
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "Sin ventana de juego en $DISP"; exit 1; }
echo "Ventana: $GW en $DISP. Medida: ${M}s por resolucion."

settle() {  # $1=WxH
  local W=${1%x*} H=${1#*x}
  DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H" 2>/dev/null
  $PY -c "
import struct,time
for _ in range(80):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$W)<=6 and abs(h-$H)<=6: break
    time.sleep(0.1)
else:
    print('  AVISO: la resolucion efectiva no coincide', w, h)
time.sleep(2)"
}
measure_game() { $PY -c "
import struct,time,subprocess,sys
M=float(sys.argv[1]); shm='$SHM'
def seq():
    with open(shm,'rb') as f: return struct.unpack('IIII',f.read(16))[2]
time.sleep(3.5)
s0=seq(); t0=time.time(); mx=0
while time.time()-t0<M:
    try: mx=max(mx,int(subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits']).split()[0]))
    except Exception: pass
    time.sleep(0.3)
s1=seq(); dt=time.time()-t0
print(f'{(s1-s0)/dt:.2f} {mx}')" "$1"; }

echo "output_res,game_fps,gpu_max" > "$OUT"
for RES in $RESOLUTIONS; do
    settle "$RES"
    read GFPS GMAX < <(measure_game $M)
    # comprobar la resolucion efectiva real de la cabecera
    EFF=$($PY -c "
import struct
w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
print(f'{w}x{h}')")
    printf "  %-10s (efectiva %-10s) | juego %-7s | GPU %s%%\n" "$RES" "$EFF" "$GFPS" "$GMAX"
    echo "$RES,$GFPS,$GMAX" >> "$OUT"
done

echo ""; echo "=== RESULTADO ==="; column -t -s, "$OUT"
echo "CSV en $OUT"
