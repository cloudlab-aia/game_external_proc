#!/bin/bash
# Exp F: ¿cuándo compensa descargar la IA en la iGPU? Barre el PESO de la IA
# (N inferencias por frame = modelo N veces más pesado) y mide, para dedicada
# (IA en dGPU) vs híbrida (IA en iGPU):
#   - FPS del JUEGO (ritmo de render, = fluidez/respuesta): lo saca del buzón.
#   - FPS ENTREGADOS (frames reescalados/s por el consumidor).
#
# Hipótesis: al crecer el peso, la dedicada roba render a la dGPU y el juego se
# hunde; la híbrida mantiene el juego (dGPU libre). Existe un cruce a partir del
# cual la híbrida gana.
#
# Render fijo a 960x540 (carga la dGPU). Requiere juego en vivo capturándose,
# con shaders, quieto. Uso: experiments/run_expF_weight.sh [display] [seg_medida]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/expF_weight.csv"
DISP="${1:-:1}"; M="${2:-8}"; RES="960x540"; SCALE=2; IW=960; IH=540
PASSES="1 2 3 4 6 8"

[ -f "$SHM" ] || { echo "No hay captura. ¿Juego en $DISP?"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "Sin ventana de juego en $DISP"; exit 1; }
echo "Ventana: $GW | render fijo $RES (x$SCALE -> 1080p)"

# fijar el render a 960x540 y esperar a que el buzón lo refleje
DISPLAY=$DISP xdotool windowsize "$GW" "$IW" "$IH" 2>/dev/null
$PY -c "
import struct,time
for _ in range(80):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$IW)<=4 and abs(h-$IH)<=4: break
    time.sleep(0.1)
time.sleep(2)"

echo "passes,device,game_fps,delivered_fps,gpu_max" > "$OUT"

# mide FPS del juego (delta de seq) + GPU máx durante M s, tras dejar pasar el calentamiento
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

for N in $PASSES; do
  for DEV in dGPU iGPU; do
    # consumidor cargando el dispositivo (mide su ritmo entregado en paralelo)
    $PY experiments/upscale_consumer.py --device $DEV --scale $SCALE --in_w $IW --in_h $IH \
        --passes $N --measure_secs $((M+6)) --warmup_secs 2 >/tmp/f_cons.log 2>&1 &
    CPID=$!
    read GFPS GMAX < <(measure_game $M)   # FPS juego + GPU máx durante la carga
    wait $CPID 2>/dev/null
    DELIV=$(grep OUTPUT_FPS /tmp/f_cons.log | cut -d= -f2)
    tag="híbrida "; [ "$DEV" = dGPU ] && tag="dedicada"
    printf "  peso x%-2s %s | juego %-6s FPS | entregados %-6s FPS | GPU %s%%\n" "$N" "$tag" "$GFPS" "${DELIV:-ERR}" "$GMAX"
    echo "$N,$DEV,$GFPS,${DELIV:-0},$GMAX" >> "$OUT"
  done
done

echo ""; echo "=== RESULTADO ==="; column -t -s, "$OUT"

# Gráficas: FPS-juego vs peso, y FPS-entregados vs peso (dedicada vs híbrida)
$PY - <<'PYEOF'
import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=list(csv.DictReader(open("results/experiments/expF_weight.csv")))
outd="results/experiments/plots"; os.makedirs(outd,exist_ok=True)
def series(dev,col):
    pts=sorted([(int(r["passes"]),float(r[col])) for r in rows if r["device"]==dev])
    return [p[0] for p in pts],[p[1] for p in pts]
col={"dGPU":"#e8a000","iGPU":"#27ae60"}; lab={"dGPU":"Dedicada (IA dGPU)","iGPU":"Híbrida (IA iGPU)"}
for metric,ylab,fn,title in [
    ("game_fps","FPS del juego (fluidez)","expF_game_fps.png","Fluidez del juego vs peso de la IA"),
    ("delivered_fps","FPS entregados (imagen final)","expF_delivered.png","FPS entregados vs peso de la IA")]:
    plt.figure(figsize=(8,5))
    for dev in ("dGPU","iGPU"):
        x,y=series(dev,metric); plt.plot(x,y,"o-",color=col[dev],lw=2,label=lab[dev])
    plt.xlabel("Peso de la IA (inferencias por frame)"); plt.ylabel(ylab); plt.title(title)
    plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
    plt.savefig(os.path.join(outd,fn),dpi=130); plt.close(); print("  "+fn)
PYEOF
echo "Gráficas en results/experiments/plots/expF_*.png"
