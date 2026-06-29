#!/bin/bash
# Matriz de carga para la configuración elegida (FSRCNN convertido a OpenVINO).
#
# Mide la latencia/FPS de inferencia de FSRCNN en cada dispositivo bajo los 4
# estados de carga (idle, CPU, iGPU, dGPU), para responder: ¿cuánto se degrada
# cada dispositivo cuando otro está saturado? y ¿la dGPU cae por debajo de la
# iGPU bajo carga? Complementa el estudio de viabilidad (Fase 1) con la config
# final, que la matriz original no cubrió.
#
# Dispositivos:
#   iGPU_OV  → FSRCNN IR (la configuración elegida)
#   CPU_OV   → FSRCNN IR en CPU (comparación)
#   dGPU_OCL → FSRCNN .pb por OpenCL (la dGPU no ejecuta IR de OpenVINO)
#
# Uso:  cd benchmarks && ./run_load_matrix.sh

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"; [ -x "$PY" ] || PY="python3"
BENCH="benchmarks/viability/benchmark_standalone.py"
STRESS="benchmarks/viability/stressors"
IR="models/openvino_ir/FSRCNN_x4.xml"
PB="models/FSRCNN_x4.pb"
INP="480 270"
OUT="results/load_matrix_fsrcnn.csv"
rm -f "$OUT"

# Modelo para los stressors de GPU (en este repo, no en el repo viejo)
export STRESS_MODEL="$PWD/models/RealESRGAN_x4.onnx"

start_stress() {  # $1 = idle|cpu|igpu|dgpu
    case "$1" in
        cpu)  $PY "$STRESS/cpu_stress.py" &  STRESS_PID=$! ;;
        igpu) $PY "$STRESS/igpu_stress.py" & STRESS_PID=$! ;;
        dgpu) $PY "$STRESS/dgpu_stress.py" & STRESS_PID=$! ;;
        *)    STRESS_PID="" ;;
    esac
    [ -n "$STRESS_PID" ] && sleep 4   # dejar que la carga arranque
}
stop_stress() { [ -n "$STRESS_PID" ] && kill "$STRESS_PID" 2>/dev/null && sleep 2; STRESS_PID=""; }

run_cell() {  # $1 device, $2 model, $3 load
    echo "[$1 / carga=$3] midiendo..."
    start_stress "$3"
    $PY "$BENCH" --model "$2" --device "$1" --input_size $INP \
        --warmup 5 --iters 40 --load_tag "$3" --out_csv "$OUT" 2>/dev/null \
        | grep -E "^\[OK\]|^\[ERROR\]" || echo "  (fallo en $1/$3)"
    stop_stress
}

for load in idle cpu igpu dgpu; do
    run_cell iGPU_OV  "$IR" "$load"
    run_cell CPU_OV   "$IR" "$load"
    run_cell dGPU_OCL "$PB" "$load"
done

echo ""
echo "=== Resumen (FPS p50 por dispositivo y carga) ==="
$PY - <<'EOF'
import csv, collections
rows = list(csv.DictReader(open("results/load_matrix_fsrcnn.csv")))
loads = ["idle","cpu","igpu","dgpu"]
devs = ["iGPU_OV","CPU_OV","dGPU_OCL"]
t = collections.defaultdict(dict)
for r in rows:
    t[r["device"]][r["load_tag"]] = float(r["fps_p50"])
print(f"{'dispositivo':<10}" + "".join(f"{l:>10}" for l in loads))
for d in devs:
    print(f"{d:<10}" + "".join(f"{t[d].get(l,0):>10.1f}" for l in loads))
EOF
echo ""
echo "CSV completo en $OUT"
