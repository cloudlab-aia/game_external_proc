#!/bin/bash
# Exp E: FPS FINALES por escala --- nativa vs dedicada vs híbrida.
#
#   nativa   = el juego dibuja a 1080p directo, sin IA (la forma tradicional).
#   dedicada = dibuja a baja resolución + IA en la dGPU (todo en la potente).
#   híbrida  = dibuja a baja resolución + IA en la iGPU (la potente queda libre).
#
# Métrica: FPS finales entregados (ritmo real de frames 1080p producidos).
#   - nativa:            ritmo de render a 1080p (contador del buzón).
#   - dedicada/híbrida:  ritmo de salida del consumidor de IA (frames reescalados/s).
#
# Objetivo: encontrar la (entrada×escala) donde la HÍBRIDA gana. Requiere la
# gráfica bien cargada -> juego con shaders PESADOS (Photon calidad alta).
#
# REQUISITOS: juego en vivo capturándose en :2, con shaders. Quieto durante la
# medida. Xvfb :2 debe ser >= 1920x1080 (para la fila nativa).
#
# Uso:  experiments/run_expE_hybrid.sh [segundos_por_medida]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="results/experiments/expE_hybrid_vs_dedicated.csv"
MSECS="${1:-10}"; DISP="${2:-:2}"; WARM=3

[ -f "$SHM" ] || { echo "No hay captura en $SHM. ¿Juego en $DISP?"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "No encuentro la ventana del juego en $DISP"; exit 1; }
echo "Ventana del juego: $GW"
echo "scale,input_res,config,fps_final,gpu_max" > "$OUT"

settle() {  # $1 = WxH : redimensiona el juego y espera a que el buzón lo refleje
  local W=${1%x*} H=${1#*x}
  DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H" 2>/dev/null
  $PY -c "
import struct,time
for _ in range(80):
    w,h,_,_=struct.unpack('IIII',open('$SHM','rb').read(16))
    if abs(w-$W)<=4 and abs(h-$H)<=4: break
    time.sleep(0.1)
time.sleep(2)"
}

# Muestrea la utilización máx. de la dGPU mientras el proceso $1 siga vivo.
sample_until() { $PY -c "
import subprocess,time,sys,os
pid=int(sys.argv[1]); mx=0
def alive(p):
    try: os.kill(p,0); return True
    except OSError: return False
while alive(pid):
    try: mx=max(mx,int(subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits']).split()[0]))
    except Exception: pass
    time.sleep(0.4)
print(mx)" "$1"; }

declare -A INP=( [2]=960x540 [3]=640x360 [4]=480x270 )
for S in 2 3 4; do
  IN=${INP[$S]}; IW=${IN%x*}; IH=${IN#*x}
  echo "===== ESCALA x$S (entrada $IN -> salida 1080p) ====="

  # 1) NATIVA: render 1080p directo, sin IA
  settle 1920x1080
  $PY benchmarks/render_fps.py --seconds $MSECS --interval $MSECS >/tmp/e_nat.log 2>&1 &
  P=$!; G=$(sample_until $P); wait $P 2>/dev/null
  F=$(grep "de media" /tmp/e_nat.log | grep -oE "[0-9]+\.[0-9]+" | head -1)
  echo "  nativa 1080p:        ${F:-ERR} FPS  | GPU max ${G}%"
  echo "$S,1920x1080,nativa,${F:-0},$G" >> "$OUT"

  # 2) DEDICADA: render bajo + IA en dGPU (compite con el render)
  settle "$IN"
  $PY experiments/upscale_consumer.py --device dGPU --scale $S --in_w $IW --in_h $IH \
      --measure_secs $MSECS --warmup_secs $WARM >/tmp/e_ded.log 2>&1 &
  P=$!; G=$(sample_until $P); wait $P 2>/dev/null
  F=$(grep OUTPUT_FPS /tmp/e_ded.log | cut -d= -f2)
  echo "  dedicada (IA dGPU):  ${F:-ERR} FPS  | GPU max ${G}%"
  echo "$S,$IN,dedicada,${F:-0},$G" >> "$OUT"

  # 3) HÍBRIDA: render bajo + IA en iGPU (la dGPU queda libre)
  $PY experiments/upscale_consumer.py --device iGPU --scale $S --in_w $IW --in_h $IH \
      --measure_secs $MSECS --warmup_secs $WARM >/tmp/e_hyb.log 2>&1 &
  P=$!; G=$(sample_until $P); wait $P 2>/dev/null
  F=$(grep OUTPUT_FPS /tmp/e_hyb.log | cut -d= -f2)
  echo "  híbrida  (IA iGPU):  ${F:-ERR} FPS  | GPU max ${G}%"
  echo "$S,$IN,hibrida,${F:-0},$G" >> "$OUT"
done

echo ""; echo "=== RESULTADO (FPS finales) ==="; column -t -s, "$OUT"

# Gráficas: 1 barras por escala (nativa/dedicada/híbrida)
$PY - <<'PYEOF'
import csv, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
REPO=os.path.dirname(os.path.dirname(os.path.abspath("experiments/x")))
csvp="results/experiments/expE_hybrid_vs_dedicated.csv"
rows=list(csv.DictReader(open(csvp)))
outd="results/experiments/plots"; os.makedirs(outd,exist_ok=True)
byscale={}
for r in rows: byscale.setdefault(r["scale"],{})[r["config"]]=float(r["fps_final"])
order=["nativa","dedicada","hibrida"]; labels=["Nativa\n(1080p)","Dedicada\n(IA dGPU)","Híbrida\n(IA iGPU)"]
cols=["#c0392b","#e8a000","#27ae60"]
for s,d in sorted(byscale.items()):
    vals=[d.get(c,0) for c in order]
    plt.figure(figsize=(6.5,5))
    b=plt.bar(range(3),vals,color=cols,width=0.6)
    for i,v in enumerate(vals): plt.text(i,v+0.3,f"{v:.1f}",ha="center",fontweight="bold")
    plt.xticks(range(3),labels); plt.ylabel("FPS finales (1080p entregados)")
    plt.title(f"FPS finales por arquitectura, escala x{s}")
    if vals[2]>vals[1]: plt.text(0.5,max(vals)*0.9,"la híbrida GANA",ha="center",color="#27ae60",fontsize=12,fontweight="bold",transform=plt.gca().get_xaxis_transform())
    plt.grid(axis="y",alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outd,f"expE_x{s}.png"),dpi=130); plt.close()
    print(f"  plot expE_x{s}.png")
PYEOF
echo "Gráficas en results/experiments/plots/expE_x{2,3,4}.png"
