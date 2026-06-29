#!/bin/bash
# Exp B (gradiente) — Cruce: inferencia FSRCNN en dGPU vs iGPU a niveles
# CRECIENTES de carga de la dGPU (0..N stressors CUDA). Muestra cómo la ventaja
# de la dGPU se reduce conforme se satura, acercándose a la iGPU (que es estable).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
BENCH="experiments/bench_inference.py"
STRESS="benchmarks/viability/stressors/dgpu_stress.py"
OUT="results/experiments/expB_gradient.csv"
rm -f "$OUT"
export STRESS_MODEL="$PWD/models/RealESRGAN_x4.onnx"
SCALE=4; W=480; H=270
MAXLOAD="${1:-4}"   # nº máximo de stressors

SPIDS=()
add_stressor() { $PY "$STRESS" >/dev/null 2>&1 & SPIDS+=($!); sleep 5; }
kill_all() { for p in "${SPIDS[@]}"; do kill "$p" 2>/dev/null; done; for p in "${SPIDS[@]}"; do wait "$p" 2>/dev/null; done; SPIDS=(); sleep 2; }

for n in $(seq 0 "$MAXLOAD"); do
  while [ "${#SPIDS[@]}" -lt "$n" ]; do add_stressor; done
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
  echo "### $n stressors → dGPU util ${util}%"
  for dev in dGPU iGPU; do
    $PY "$BENCH" --device "$dev" --scale $SCALE --in_w $W --in_h $H \
      --warmup 5 --iters 50 --load_tag "load${n}_util${util}" --out_csv "$OUT" 2>&1 | grep -E "OK|ERROR"
  done
done
kill_all

echo ""
echo "=== Gradiente: FPS p50 de inferencia vs carga dGPU ==="
$PY - <<'EOF'
import csv, collections
rows=list(csv.DictReader(open("results/experiments/expB_gradient.csv")))
order=[]
data=collections.defaultdict(dict)
for r in rows:
    lt=r["load_tag"]
    if lt not in order: order.append(lt)
    data[r["device"]][lt]=float(r["fps_p50"])
print(f"{'carga':<20}{'dGPU':>8}{'iGPU':>8}")
for lt in order:
    d=data['dGPU'].get(lt,0); i=data['iGPU'].get(lt,0)
    mark=" <-- CRUCE" if i>=d else ""
    print(f"{lt:<20}{d:>8.0f}{i:>8.0f}{mark}")
EOF
