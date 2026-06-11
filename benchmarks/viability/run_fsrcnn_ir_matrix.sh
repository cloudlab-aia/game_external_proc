#!/usr/bin/env bash
# run_fsrcnn_ir_matrix.sh
#
# Matriz para FSRCNN convertido a OpenVINO IR (.xml/.bin).
# Solo CPU_OV y iGPU_OV — únicos backends que ejecutan IR.
# Reutiliza stressors de run_viability_matrix.sh para idle/cpu/igpu/dgpu.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH="$SCRIPT_DIR/benchmark_standalone.py"
RESULT_CSV="$SCRIPT_DIR/results/viability_results_fsrcnn_ir.csv"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR" "$SCRIPT_DIR/results"

NV=/home/ogg/.local/lib/python3.13/site-packages/nvidia
export LD_LIBRARY_PATH="$NV/cublas/lib:$NV/cudnn/lib:$NV/cuda_runtime/lib:$NV/cufft/lib:$NV/curand/lib:$NV/cusolver/lib:$NV/cusparse/lib:$NV/nvjitlink/lib:$NV/cuda_nvrtc/lib:$NV/nccl/lib:$NV/cuda_cupti/lib:${LD_LIBRARY_PATH:-}"

WARMUP=5
ITERS=30
RUN_ID="fsrcnn_ir_$(date +%Y%m%dT%H%M%S)"
echo "=== FSRCNN IR Matrix: $RUN_ID  warmup=$WARMUP iters=$ITERS ==="

CPU_STRESS_PID=""
IGPU_STRESS_PID=""
DGPU_STRESS_PID=""

start_load() {
  local mode="$1"
  case "$mode" in
    idle) ;;
    cpu)
      stress --cpu 16 --timeout 7200 > "$LOG_DIR/cpu_stress_${RUN_ID}.log" 2>&1 &
      CPU_STRESS_PID=$!
      sleep 1
      ;;
    igpu)
      python3 "$SCRIPT_DIR/stressors/igpu_stress.py" > "$LOG_DIR/igpu_stress_${RUN_ID}.log" 2>&1 &
      IGPU_STRESS_PID=$!
      for _ in $(seq 1 60); do
        grep -q "iGPU_STRESS_READY" "$LOG_DIR/igpu_stress_${RUN_ID}.log" 2>/dev/null && break
        sleep 0.5
      done
      ;;
    dgpu)
      python3 "$SCRIPT_DIR/stressors/dgpu_stress.py" > "$LOG_DIR/dgpu_stress_${RUN_ID}.log" 2>&1 &
      DGPU_STRESS_PID=$!
      for _ in $(seq 1 60); do
        grep -q "dGPU_STRESS_READY" "$LOG_DIR/dgpu_stress_${RUN_ID}.log" 2>/dev/null && break
        sleep 0.5
      done
      ;;
  esac
}

stop_load() {
  local mode="$1"
  case "$mode" in
    cpu)
      [[ -n "$CPU_STRESS_PID" ]] && kill "$CPU_STRESS_PID" 2>/dev/null || true
      pkill -x stress 2>/dev/null || true
      CPU_STRESS_PID=""
      ;;
    igpu)
      [[ -n "$IGPU_STRESS_PID" ]] && kill "$IGPU_STRESS_PID" 2>/dev/null || true
      IGPU_STRESS_PID=""
      ;;
    dgpu)
      [[ -n "$DGPU_STRESS_PID" ]] && kill "$DGPU_STRESS_PID" 2>/dev/null || true
      DGPU_STRESS_PID=""
      ;;
  esac
  sleep 1
}

cleanup_all() {
  stop_load cpu 2>/dev/null || true
  stop_load igpu 2>/dev/null || true
  stop_load dgpu 2>/dev/null || true
}
trap cleanup_all EXIT INT TERM

run_one() {
  local device="$1" model="$2" iw="$3" ih="$4"
  cd "$ROOT_DIR"
  python3 "$BENCH" \
    --device "$device" \
    --model "models/openvino_ir/$model" \
    --input_size "$iw" "$ih" \
    --warmup "$WARMUP" \
    --iters "$ITERS" \
    --load_tag "$LOAD" \
    --out_csv "$RESULT_CSV" \
    --run_id "$RUN_ID" \
    2>>"$LOG_DIR/bench_${RUN_ID}.err" | tail -1
}

# Matriz: misma cobertura de resoluciones que FSRCNN .pb
DEVS=(CPU_OV iGPU_OV)
X2_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720" "1920 1080" )
X3_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720" )
X4_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "960 540" )

LOADS=(idle cpu igpu dgpu)

# Cuenta total
TOTAL=0
for d in "${DEVS[@]}"; do
  TOTAL=$((TOTAL + ${#X2_RES[@]} + ${#X3_RES[@]} + ${#X4_RES[@]}))
done
TOTAL=$((TOTAL * ${#LOADS[@]}))
echo "Total ejecuciones: $TOTAL"

i=0
for LOAD in "${LOADS[@]}"; do
  echo ""
  echo "===================================================="
  echo "LOAD STATE: $LOAD"
  echo "===================================================="
  start_load "$LOAD"

  for d in "${DEVS[@]}"; do
    for r in "${X2_RES[@]}"; do
      iw=$(echo "$r" | awk '{print $1}'); ih=$(echo "$r" | awk '{print $2}')
      i=$((i+1))
      printf "[%4d/%d] load=%-4s %-10s FSRCNN_x2.xml %sx%s  " "$i" "$TOTAL" "$LOAD" "$d" "$iw" "$ih"
      out=$(run_one "$d" "FSRCNN_x2.xml" "$iw" "$ih" || true)
      [[ -n "$out" ]] && echo "$out" | sed 's/^\[OK\] //' || echo "(sin salida)"
    done
    for r in "${X3_RES[@]}"; do
      iw=$(echo "$r" | awk '{print $1}'); ih=$(echo "$r" | awk '{print $2}')
      i=$((i+1))
      printf "[%4d/%d] load=%-4s %-10s FSRCNN_x3.xml %sx%s  " "$i" "$TOTAL" "$LOAD" "$d" "$iw" "$ih"
      out=$(run_one "$d" "FSRCNN_x3.xml" "$iw" "$ih" || true)
      [[ -n "$out" ]] && echo "$out" | sed 's/^\[OK\] //' || echo "(sin salida)"
    done
    for r in "${X4_RES[@]}"; do
      iw=$(echo "$r" | awk '{print $1}'); ih=$(echo "$r" | awk '{print $2}')
      i=$((i+1))
      printf "[%4d/%d] load=%-4s %-10s FSRCNN_x4.xml %sx%s  " "$i" "$TOTAL" "$LOAD" "$d" "$iw" "$ih"
      out=$(run_one "$d" "FSRCNN_x4.xml" "$iw" "$ih" || true)
      [[ -n "$out" ]] && echo "$out" | sed 's/^\[OK\] //' || echo "(sin salida)"
    done
  done

  stop_load "$LOAD"
done

echo ""
echo "=== Matriz FSRCNN IR completa. Resultados en $RESULT_CSV ==="
wc -l "$RESULT_CSV"
