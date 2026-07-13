#!/usr/bin/env bash
# run_viability_matrix.sh
#
# Orquesta la matriz completa de experimentos de viabilidad del TFG:
#   6 dispositivos (sin NPU) x N modelos x M resoluciones x 4 estados de carga.
#
# Dispositivos:
#   - CPU_OCV, iGPU_OCL, dGPU_OCL   (OpenCV DNN, modelos .pb)
#   - CPU_OV,  iGPU_OV              (OpenVINO, modelos .onnx/.xml)
#   - dGPU_CUDA                     (ONNX Runtime, modelos .onnx)
#
# Estados de carga:
#   - idle : sistema sin carga extra
#   - cpu  : stress --cpu 16   (deja 4 cores para el benchmark)
#   - igpu : bucle OpenVINO GPU saturando la iGPU
#   - dgpu : bucle ONNX Runtime CUDA saturando la dGPU
#
# Uso:
#   bash run_viability_matrix.sh                         # matriz completa
#   bash run_viability_matrix.sh --smoke                 # subset corto de verificacion
#   bash run_viability_matrix.sh --loads idle,cpu        # solo estos estados
#   bash run_viability_matrix.sh --devices CPU_OCV,iGPU_OCL
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH="$SCRIPT_DIR/benchmark_standalone.py"
RESULT_CSV="$SCRIPT_DIR/results/viability_results.csv"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR" "$SCRIPT_DIR/results"

# === Librerias CUDA bundled (onnxruntime-gpu trae sus propias) ===
NV=/home/ogg/.local/lib/python3.13/site-packages/nvidia
export LD_LIBRARY_PATH="$NV/cublas/lib:$NV/cudnn/lib:$NV/cuda_runtime/lib:$NV/cufft/lib:$NV/curand/lib:$NV/cusolver/lib:$NV/cusparse/lib:$NV/nvjitlink/lib:$NV/cuda_nvrtc/lib:$NV/nccl/lib:$NV/cuda_cupti/lib:${LD_LIBRARY_PATH:-}"

# === CLI flags ===
SMOKE=0
LOADS_FILTER=""
DEVICES_FILTER=""
WARMUP=5
ITERS=30
while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke) SMOKE=1; shift;;
    --loads)   LOADS_FILTER="$2"; shift 2;;
    --devices) DEVICES_FILTER="$2"; shift 2;;
    --warmup)  WARMUP="$2"; shift 2;;
    --iters)   ITERS="$2"; shift 2;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0;;
    *) echo "Argumento desconocido: $1"; exit 1;;
  esac
done

if [[ "$SMOKE" -eq 1 ]]; then
  WARMUP=2
  ITERS=5
fi

RUN_ID="run_$(date +%Y%m%dT%H%M%S)"
echo "=== Run ID: $RUN_ID  warmup=$WARMUP iters=$ITERS smoke=$SMOKE ==="

# =====================================================================
# Gestor de stressors: arranca / para procesos de carga segun el modo.
# =====================================================================
CPU_STRESS_PID=""
IGPU_STRESS_PID=""
DGPU_STRESS_PID=""

start_load() {
  local mode="$1"
  case "$mode" in
    idle)
      ;;
    cpu)
      # Deja 4 nucleos libres para el benchmark. 16 de carga.
      stress --cpu 16 --timeout 3600 > "$LOG_DIR/cpu_stress_${RUN_ID}.log" 2>&1 &
      CPU_STRESS_PID=$!
      sleep 1
      ;;
    igpu)
      python3 "$SCRIPT_DIR/stressors/igpu_stress.py" > "$LOG_DIR/igpu_stress_${RUN_ID}.log" 2>&1 &
      IGPU_STRESS_PID=$!
      # Espera a que el stressor imprima READY en el log.
      for _ in $(seq 1 60); do
        if grep -q "iGPU_STRESS_READY" "$LOG_DIR/igpu_stress_${RUN_ID}.log" 2>/dev/null; then
          break
        fi
        sleep 0.5
      done
      ;;
    dgpu)
      python3 "$SCRIPT_DIR/stressors/dgpu_stress.py" > "$LOG_DIR/dgpu_stress_${RUN_ID}.log" 2>&1 &
      DGPU_STRESS_PID=$!
      for _ in $(seq 1 60); do
        if grep -q "dGPU_STRESS_READY" "$LOG_DIR/dgpu_stress_${RUN_ID}.log" 2>/dev/null; then
          break
        fi
        sleep 0.5
      done
      ;;
    *) echo "Modo de carga desconocido: $mode"; return 1;;
  esac
}

stop_load() {
  local mode="$1"
  case "$mode" in
    idle) ;;
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

# =====================================================================
# Helper de ejecucion de benchmark. Segundo parametro fija OPENCV_OPENCL_DEVICE.
# =====================================================================
run_one() {
  local device="$1" model="$2" iw="$3" ih="$4" load="$5"
  local extra_env=""
  case "$device" in
    iGPU_OCL) extra_env="OPENCV_OPENCL_DEVICE=Intel:GPU:0";;
    dGPU_OCL) extra_env="OPENCV_OPENCL_DEVICE=NVIDIA:GPU:0";;
  esac

  cd "$ROOT_DIR"
  env $extra_env python3 "$BENCH" \
    --device "$device" \
    --model "models/$model" \
    --input_size "$iw" "$ih" \
    --warmup "$WARMUP" \
    --iters "$ITERS" \
    --load_tag "$load" \
    --out_csv "$RESULT_CSV" \
    --run_id "$RUN_ID" \
    2>>"$LOG_DIR/bench_${RUN_ID}.err" | tail -1
}

# =====================================================================
# Definicion de la matriz de experimentos.
# Formato por linea: "DEVICE,MODEL,W,H"
# =====================================================================
build_matrix() {
  local OUT="$1"
  : > "$OUT"

  # ---- FSRCNN (.pb) --------------------------------------------------
  # Resoluciones: pensadas para que la salida (input * factor) no explote.
  local FSRCNN_DEVS=(CPU_OCV iGPU_OCL dGPU_OCL)
  local FSRCNN_X2_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720" "1920 1080" )
  local FSRCNN_X3_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720" )
  local FSRCNN_X4_RES=( "128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "960 540" )

  if [[ "$SMOKE" -eq 1 ]]; then
    FSRCNN_X2_RES=( "320 240" "640 480" )
    FSRCNN_X3_RES=( "320 240" )
    FSRCNN_X4_RES=( "320 240" )
  fi

  for d in "${FSRCNN_DEVS[@]}"; do
    for r in "${FSRCNN_X2_RES[@]}"; do echo "$d,FSRCNN_x2.pb,$r" >> "$OUT"; done
    for r in "${FSRCNN_X3_RES[@]}"; do echo "$d,FSRCNN_x3.pb,$r" >> "$OUT"; done
    for r in "${FSRCNN_X4_RES[@]}"; do echo "$d,FSRCNN_x4.pb,$r" >> "$OUT"; done
  done

  # ---- ONNX fixed-shape (super-resolution-10, RealESRGAN_x4) ---------
  # Estos modelos tienen reshape interno hardcoded a 224x224.
  # OpenVINO y ONNX Runtime CUDA solo funcionan a 224x224.
  local ONNX_RES_OV=( "224 224" )
  local ONNX_RES_CUDA=( "224 224" )

  if [[ "$SMOKE" -eq 1 ]]; then
    ONNX_RES_OV=( "224 224" )
    ONNX_RES_CUDA=( "224 224" )
  fi

  for m in "super-resolution-10.onnx" "RealESRGAN_x4.onnx"; do
    for d in CPU_OV iGPU_OV; do
      for r in "${ONNX_RES_OV[@]}"; do echo "$d,$m,$r" >> "$OUT"; done
    done
    for r in "${ONNX_RES_CUDA[@]}"; do echo "dGPU_CUDA,$m,$r" >> "$OUT"; done
  done

  # ---- OpenVINO IR (single-image-super-resolution-1032) --------------
  # Shape fijo 270x480 y segunda entrada bicubica; solo CPU_OV/iGPU_OV.
  for d in CPU_OV iGPU_OV; do
    echo "$d,single-image-super-resolution-1032.xml,480 270" >> "$OUT"
  done
}

MATRIX_FILE="$LOG_DIR/matrix_${RUN_ID}.txt"
build_matrix "$MATRIX_FILE"
N_CELLS=$(wc -l < "$MATRIX_FILE")
echo "Celdas por estado de carga: $N_CELLS"

LOADS=(idle cpu igpu dgpu)
if [[ -n "$LOADS_FILTER" ]]; then
  IFS=',' read -r -a LOADS <<< "$LOADS_FILTER"
  IFS=$' \t\n'
fi

N_LOADS=${#LOADS[@]}
TOTAL=$(( N_CELLS * N_LOADS ))
echo "Estados: ${LOADS[*]}   Total ejecuciones: $TOTAL"

i=0
for load in "${LOADS[@]}"; do
  echo ""
  echo "===================================================="
  echo "LOAD STATE: $load"
  echo "===================================================="
  start_load "$load"

  while IFS=',' read -r device model res; do
    # Filtro opcional por dispositivo
    if [[ -n "$DEVICES_FILTER" && ",$DEVICES_FILTER," != *",$device,"* ]]; then
      continue
    fi
    iw=$(echo "$res" | awk '{print $1}')
    ih=$(echo "$res" | awk '{print $2}')
    i=$((i+1))
    printf "[%4d/%d] load=%-4s %-10s %-40s %sx%s  " \
      "$i" "$TOTAL" "$load" "$device" "$model" "$iw" "$ih"
    out=$(run_one "$device" "$model" "$iw" "$ih" "$load" || true)
    # La salida del benchmark es [OK] ...  o [SKIP]/[ERROR]
    if [[ -z "$out" ]]; then
      echo "(sin salida, revisar $LOG_DIR/bench_${RUN_ID}.err)"
    else
      echo "$out" | sed 's/^\[OK\] //'
    fi
  done < "$MATRIX_FILE"

  stop_load "$load"
done

echo ""
echo "=== Matriz completa. Resultados en $RESULT_CSV ==="
wc -l "$RESULT_CSV"
