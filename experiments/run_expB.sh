#!/bin/bash
# Exp B, Cruce bajo carga: FSRCNN en cada dispositivo bajo cada estado de
# carga. Pregunta clave: cuando la dGPU está saturada (≈ renderizando el
# juego), ¿su inferencia cae por debajo de la iGPU (libre)?
#
# Carga sintética. La carga REAL (shaders) se mide en Exp C.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
BENCH="experiments/bench_inference.py"
STRESS="benchmarks/viability/stressors"
OUT="results/experiments/expB_crossover.csv"
rm -f "$OUT"
export STRESS_MODEL="$PWD/models/RealESRGAN_x4.onnx"

# resolución/escala representativas (la salida 1080p de la arquitectura)
SCALE=4; W=480; H=270

start_stress() {
  case "$1" in
    cpu)  $PY "$STRESS/cpu_stress.py" &  SPID=$! ;;
    igpu) $PY "$STRESS/igpu_stress.py" & SPID=$! ;;
    dgpu) $PY "$STRESS/dgpu_stress.py" & SPID=$! ;;
    *)    SPID="" ;;
  esac
  [ -n "$SPID" ] && sleep 5
}
stop_stress() { [ -n "$SPID" ] && { kill "$SPID" 2>/dev/null; wait "$SPID" 2>/dev/null; sleep 2; }; SPID=""; }

for load in idle cpu igpu dgpu; do
  echo "### carga = $load"
  start_stress "$load"
  for dev in dGPU iGPU CPU; do
    $PY "$BENCH" --device "$dev" --scale $SCALE --in_w $W --in_h $H \
      --warmup 5 --iters 50 --load_tag "$load" --out_csv "$OUT" 2>&1 | grep -E "OK|ERROR"
  done
  stop_stress
done

echo ""
echo "=== Resumen FPS p50 (dispositivo × carga) ==="
$PY - <<'EOF'
import csv, collections
t = collections.defaultdict(dict)
for r in csv.DictReader(open("results/experiments/expB_crossover.csv")):
    t[r["device"]][r["load_tag"]] = float(r["fps_p50"])
loads = ["idle","cpu","igpu","dgpu"]
print(f"{'disp':<6}" + "".join(f"{l:>9}" for l in loads))
for d in ["dGPU","iGPU","CPU"]:
    print(f"{d:<6}" + "".join(f"{t[d].get(l,0):>9.0f}" for l in loads))
print("\nCruce: comparar columna 'dgpu' (dGPU cargada), ¿iGPU > dGPU?")
EOF
