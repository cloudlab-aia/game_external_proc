#!/usr/bin/env bash
# run_quality_showcase.sh
#
# Ejecuta benchmark de calidad visual (idle, sin carga):
#   - Usa frames de test estructurados (o imagen real con --image)
#   - Guarda imágenes comparativas input/bicubico/modelo en results/sample_outputs/
#   - Calcula PSNR y SSIM vs bicubico para cada celda
#   - Escribe resultados en results/quality_results.csv
#
# Uso:
#   bash run_quality_showcase.sh                          # frames sintéticos
#   bash run_quality_showcase.sh --image /ruta/foto.jpg   # imagen real
#   bash run_quality_showcase.sh --scene checkerboard     # otro tipo de frame
#   bash run_quality_showcase.sh --smoke                  # subset rapido
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH="$SCRIPT_DIR/benchmark_standalone.py"
RESULT_CSV="$SCRIPT_DIR/results/quality_results.csv"
IMG_DIR="$SCRIPT_DIR/results/sample_outputs"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR" "$SCRIPT_DIR/results" "$IMG_DIR"

NV=/home/ogg/.local/lib/python3.13/site-packages/nvidia
export LD_LIBRARY_PATH="$NV/cublas/lib:$NV/cudnn/lib:$NV/cuda_runtime/lib:$NV/cufft/lib:$NV/curand/lib:$NV/cusolver/lib:$NV/cusparse/lib:$NV/nvjitlink/lib:$NV/cuda_nvrtc/lib:$NV/nccl/lib:$NV/cuda_cupti/lib:${LD_LIBRARY_PATH:-}"

SMOKE=0
IMAGE_ARG=""
SCENE="mixed"
WARMUP=3
ITERS=10

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke)  SMOKE=1; shift;;
    --image)  IMAGE_ARG="--image $2"; shift 2;;
    --scene)  SCENE="$2"; shift 2;;
    --warmup) WARMUP="$2"; shift 2;;
    --iters)  ITERS="$2"; shift 2;;
    -h|--help) sed -n '2,15p' "$0"; exit 0;;
    *) echo "Argumento desconocido: $1"; exit 1;;
  esac
done

if [[ "$SMOKE" -eq 1 ]]; then
  WARMUP=1; ITERS=3
fi

RUN_ID="quality_$(date +%Y%m%dT%H%M%S)"
echo "=== Quality Showcase: $RUN_ID  warmup=$WARMUP iters=$ITERS ==="
[[ -n "$IMAGE_ARG" ]] && echo "Imagen: $IMAGE_ARG" || echo "Frame tipo: $SCENE"

run_one() {
  local device="$1" model="$2" iw="$3" ih="$4"
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
    --warmup "$WARMUP" --iters "$ITERS" \
    --load_tag idle \
    --scene_type "$SCENE" \
    $IMAGE_ARG \
    --save_outputs \
    --out_images_dir "$IMG_DIR" \
    --out_csv "$RESULT_CSV" \
    --run_id "$RUN_ID" \
    2>>"$LOG_DIR/quality_${RUN_ID}.err" | tail -1 || true
}

echo ""
echo "── FSRCNN (CPU_OCV / iGPU_OCL / dGPU_OCL) ──────────────────────────────"
FSRCNN_DEVS=(CPU_OCV iGPU_OCL dGPU_OCL)

if [[ "$SMOKE" -eq 1 ]]; then
  FSRCNN_X2_RES=("320 180" "640 360")
  FSRCNN_X3_RES=("320 180")
  FSRCNN_X4_RES=("320 180")
else
  FSRCNN_X2_RES=("128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720" "1920 1080")
  FSRCNN_X3_RES=("128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "800 600" "960 540" "1280 720")
  FSRCNN_X4_RES=("128 72" "256 144" "320 180" "480 270" "640 360" "640 480" "960 540")
fi

for d in "${FSRCNN_DEVS[@]}"; do
  for r in "${FSRCNN_X2_RES[@]}"; do
    printf "  %-10s FSRCNN_x2.pb %s  " "$d" "$r"
    run_one "$d" FSRCNN_x2.pb $r
  done
  for r in "${FSRCNN_X3_RES[@]}"; do
    printf "  %-10s FSRCNN_x3.pb %s  " "$d" "$r"
    run_one "$d" FSRCNN_x3.pb $r
  done
  for r in "${FSRCNN_X4_RES[@]}"; do
    printf "  %-10s FSRCNN_x4.pb %s  " "$d" "$r"
    run_one "$d" FSRCNN_x4.pb $r
  done
done

echo ""
echo "── ONNX / OV (CPU_OV / iGPU_OV) ────────────────────────────────────────"
OV_RES=("224 224")
for m in super-resolution-10.onnx RealESRGAN_x4.onnx; do
  for d in CPU_OV iGPU_OV; do
    for r in "${OV_RES[@]}"; do
      printf "  %-10s %-38s %s  " "$d" "$m" "$r"
      run_one "$d" "$m" $r
    done
  done
done
# CUDA
for m in super-resolution-10.onnx RealESRGAN_x4.onnx; do
  printf "  %-10s %-38s 224 224  " "dGPU_CUDA" "$m"
  run_one dGPU_CUDA "$m" 224 224
done

echo ""
echo "── OpenVINO IR (SISR-1032) ──────────────────────────────────────────────"
for d in CPU_OV iGPU_OV; do
  printf "  %-10s single-image-super-resolution-1032.xml 480 270  " "$d"
  run_one "$d" single-image-super-resolution-1032.xml 480 270
done

echo ""
echo "=== Quality showcase completo. ==="
echo "Imágenes en: $IMG_DIR"
echo "CSV en:      $RESULT_CSV"
wc -l "$RESULT_CSV" 2>/dev/null || true
