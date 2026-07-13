#!/bin/bash
# Exp G: barrido de RESOLUCIONES de entrada por factor de escala, híbrida vs
# dedicada, midiendo FPS del JUEGO (fluidez) y FPS entregados. Una gráfica por
# escala (x2/x3/x4). Peso de IA real (1 inferencia/frame).
#
# Para cada (escala, resolución de entrada):
#   dedicada = IA en dGPU (compite con el render)   |   híbrida = IA en iGPU
#   se mide el FPS de render del juego mientras el consumidor carga el dispositivo.
#
# REQUISITOS: juego en vivo capturándose, en un mundo, quieto. Uso:
#   experiments/run_expG_resolution.sh [display] [seg_medida]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/expG_resolution.csv"
DISP="${1:-:2}"; M="${2:-8}"; WARM=3
INPUTS="320x180 480x270 640x360 854x480 960x540"
SCALES="2 3 4"

[ -f "$SHM" ] || { echo "No hay captura. ¿Juego en $DISP?"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "Sin ventana de juego en $DISP"; exit 1; }
echo "Ventana: $GW en $DISP"

settle() {  # $1=WxH
  local W=${1%x*} H=${1#*x}
  DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H" 2>/dev/null
  $PY -c "
import struct,time
for _ in range(80):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$W)<=6 and abs(h-$H)<=6: break
    time.sleep(0.1)
time.sleep(2)"
}
# FPS del juego (delta seq) + GPU máx durante M s, tras el calentamiento
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

echo "scale,input_res,device,game_fps,delivered_fps,gpu_max" > "$OUT"
for S in $SCALES; do
  echo "===== ESCALA x$S ====="
  for IN in $INPUTS; do
    IW=${IN%x*}; IH=${IN#*x}
    settle "$IN"
    for DEV in dGPU iGPU; do
      $PY experiments/upscale_consumer.py --device $DEV --scale $S --in_w $IW --in_h $IH \
          --measure_secs $((M+6)) --warmup_secs $WARM >/tmp/g_cons.log 2>&1 &
      CPID=$!
      read GFPS GMAX < <(measure_game $M)
      wait $CPID 2>/dev/null
      DELIV=$(grep OUTPUT_FPS /tmp/g_cons.log | cut -d= -f2)
      tag="híbrida "; [ "$DEV" = dGPU ] && tag="dedicada"
      printf "  x%s %-8s %s | juego %-6s | entreg %-6s | GPU %s%%\n" "$S" "$IN" "$tag" "$GFPS" "${DELIV:-ERR}" "$GMAX"
      echo "$S,$IN,$DEV,$GFPS,${DELIV:-0},$GMAX" >> "$OUT"
    done
  done
done

echo ""; echo "=== RESULTADO ==="; column -t -s, "$OUT"

# Gráficas: 1 por escala, FPS del juego vs resolución de entrada (dedicada vs híbrida)
$PY - <<'PYEOF'
import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=list(csv.DictReader(open("results/experiments/expG_resolution.csv")))
outd="results/experiments/plots"; os.makedirs(outd,exist_ok=True)
col={"dGPU":"#e8a000","iGPU":"#27ae60"}; lab={"dGPU":"Dedicada (IA dGPU)","iGPU":"Híbrida (IA iGPU)"}
scales=sorted(set(r["scale"] for r in rows))
def px(res): w,h=res.split("x"); return int(w)*int(h)/1000
for s in scales:
    plt.figure(figsize=(8,5))
    for dev in ("dGPU","iGPU"):
        pts=sorted([(px(r["input_res"]),float(r["game_fps"]),r["input_res"]) for r in rows if r["scale"]==s and r["device"]==dev])
        if pts: plt.plot([p[0] for p in pts],[p[1] for p in pts],"o-",color=col[dev],lw=2,label=lab[dev])
    xs=sorted(set(px(r["input_res"]) for r in rows if r["scale"]==s))
    names=[next(r["input_res"] for r in rows if px(r["input_res"])==x) for x in xs]
    plt.xticks(xs,names,rotation=25,fontsize=8)
    plt.xlabel("Resolución de render (entrada)"); plt.ylabel("FPS del juego (fluidez)")
    plt.title(f"FPS del juego vs resolución de render, escala x{s}")
    plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(outd,f"expG_game_x{s}.png"),dpi=130); plt.close(); print(f"  expG_game_x{s}.png")
PYEOF
echo "Gráficas en results/experiments/plots/expG_game_x{2,3,4}.png"
