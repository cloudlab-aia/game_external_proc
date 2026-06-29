#!/bin/bash
# Exp A — Barrido de inferencia SIN carga: FSRCNN en dGPU vs iGPU vs CPU,
# por resolución de entrada y factor de escala. Mapa base de qué dispositivo
# gana en cada combinación en reposo.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
BENCH="experiments/bench_inference.py"
OUT="results/experiments/expA_inference_sweep.csv"
rm -f "$OUT"

RESOLUTIONS="256x144 320x180 480x270 640x360 960x540 1280x720"
SCALES="2 3 4"
DEVICES="dGPU iGPU CPU"

for scale in $SCALES; do
  for res in $RESOLUTIONS; do
    w="${res%x*}"; h="${res#*x}"
    for dev in $DEVICES; do
      $PY "$BENCH" --device "$dev" --scale "$scale" --in_w "$w" --in_h "$h" \
        --warmup 5 --iters 50 --load_tag idle --out_csv "$OUT" 2>&1 | grep -E "OK|ERROR"
    done
  done
done
echo ""
echo "=== Exp A completo: $OUT ==="
