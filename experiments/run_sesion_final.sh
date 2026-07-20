#!/bin/bash
# Sesion de medida final honesta. Mide, en el mismo entorno y seguidas,
# las 3 configuraciones (nativa / dedicada dGPU / hibrida iGPU) con el
# PIPELINE COMPLETO, reportando render_fps (arquitectura) y visible_fps
# (lo que ve el jugador). Requiere el juego vivo en :2, en el mundo.
#
# Uso: experiments/run_sesion_final.sh [display] [seg_medida]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
DISP="${1:-:2}"; M="${2:-12}"
OUT="results/experiments/sistema_final.csv"

[ -f "$SHM" ] || { echo "No hay captura. ¿Juego vivo y en el mundo en $DISP?"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "Sin ventana de juego en $DISP"; exit 1; }
echo "Ventana del juego: $GW en $DISP"

focus() { DISPLAY=$DISP xdotool windowactivate "$GW" 2>/dev/null;
          DISPLAY=$DISP xdotool windowfocus "$GW" 2>/dev/null; }

settle() {  # $1=WxH
  local W=${1%x*} H=${1#*x}
  DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H" 2>/dev/null
  focus
  $PY -c "
import struct,time
for _ in range(80):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$W)<=6 and abs(h-$H)<=6: break
    time.sleep(0.1)
time.sleep(2)"
}

# FPS de render puro (nativa): sin consumidor, solo contador de secuencia
measure_native() { $PY -c "
import struct,time,sys
M=float(sys.argv[1]); shm='$SHM'
def seq():
    with open(shm,'rb') as f: return struct.unpack('IIII',f.read(16))[2]
time.sleep(3.5)
s0=seq(); t0=time.time()
time.sleep(M)
s1=seq(); dt=time.time()-t0
print(f'{(s1-s0)/dt:.2f}')" "$1"; }

echo "config,in_res,out_res,render_fps,visible_fps" > "$OUT"

echo ""
echo "================ CONFIG REFERENCIA (salida 1080p) ================"

# 1) NATIVA: render directo a 1080p, sin superresolucion, sin consumidor
echo "[1/3] NATIVA (render 1920x1080 directo)..."
settle "1920x1080"
focus
NFPS=$(measure_native $M)
echo "      nativa: render=$NFPS FPS (= visible, presenta directo)"
echo "nativa,1920x1080,1920x1080,$NFPS,$NFPS" >> "$OUT"

# 2) DEDICADA: render 640x360, IA en dGPU, pipeline completo
echo "[2/3] DEDICADA (render 640x360 + FSRCNN x3 en dGPU)..."
settle "640x360"; focus
R=$(DISPLAY=:1 $PY experiments/measure_system_final.py \
     --device dGPU --scale 3 --in_w 640 --in_h 360 --out_w 1920 --out_h 1080 \
     --measure_secs $M --warmup_secs 4 --display --tag dedicada 2>/dev/null | grep RESULT)
echo "      $R"
RF=$(echo "$R" | grep -oP 'render_fps=\K[0-9.]+'); VF=$(echo "$R" | grep -oP 'visible_fps=\K[0-9.]+')
echo "dedicada,640x360,1920x1080,${RF:-0},${VF:-0}" >> "$OUT"

# 3) HIBRIDA: render 640x360, IA en iGPU, pipeline completo
echo "[3/3] HIBRIDA (render 640x360 + FSRCNN x3 en iGPU)..."
settle "640x360"; focus
R=$(CUDA_VISIBLE_DEVICES="" DISPLAY=:1 $PY experiments/measure_system_final.py \
     --device iGPU --scale 3 --in_w 640 --in_h 360 --out_w 1920 --out_h 1080 \
     --measure_secs $M --warmup_secs 4 --display --tag hibrida 2>/dev/null | grep RESULT)
echo "      $R"
RF=$(echo "$R" | grep -oP 'render_fps=\K[0-9.]+'); VF=$(echo "$R" | grep -oP 'visible_fps=\K[0-9.]+')
echo "hibrida,640x360,1920x1080,${RF:-0},${VF:-0}" >> "$OUT"

# devolver la ventana a 640x360 para seguir jugando
settle "640x360"

echo ""
echo "==================== RESULTADO ===================="
column -t -s, "$OUT"
echo "CSV en $OUT"
