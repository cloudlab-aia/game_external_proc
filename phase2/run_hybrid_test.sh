#!/usr/bin/env bash
# run_hybrid_test.sh
#
# Full hybrid architecture test with Minecraft.
# Steps:
#   1. Launch Minecraft Java Edition with LD_PRELOAD wrapper at low resolution
#   2. Run hybrid_pipeline.py (iGPU FSRCNN IR) to capture upscaled frames
#   3. Compute PSNR/SSIM vs bicubic baseline
#   4. Optionally compare vs native high-res capture
#
# Usage:
#   bash FASE_2/run_hybrid_test.sh [OPTIONS]
#
# Options:
#   --scale      2|3|4       Upscale factor (default: 2)
#   --res        WxH         Game render resolution (default: 960x540 for ×2 → 1920×1080)
#   --frames     N           Frames to capture (default: 300)
#   --display                Show live SR window while capturing
#   --smoke                  Quick test: 30 frames
#   --simulate               Use simulate_game.py instead of real Minecraft
#   --no_compare             Skip metrics computation
#
# Minecraft resolution setup (Java Edition):
#   Options → Video Settings → Resolution: set to --res value
#   Or pass -Dorg.lwjgl.opengl.Display.width=960 -Dorg.lwjgl.opengl.Display.height=540
#   to the JVM (via the launcher's JVM arguments field).
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS="$SCRIPT_DIR/results"

# ── Defaults ──────────────────────────────────────────────────────────────────
SCALE=2
RES="960x540"
FRAMES=300
DISPLAY_FLAG=""
SIMULATE=0
NO_COMPARE=0
SMOKE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scale)     SCALE="$2"; shift 2;;
    --res)       RES="$2";   shift 2;;
    --frames)    FRAMES="$2";shift 2;;
    --display)   DISPLAY_FLAG="--display"; shift;;
    --simulate)  SIMULATE=1; shift;;
    --no_compare)NO_COMPARE=1; shift;;
    --smoke)     SMOKE=1; FRAMES=30; shift;;
    -h|--help)   sed -n '2,30p' "$0"; exit 0;;
    *) echo "Unknown argument: $1"; exit 1;;
  esac
done

RES_W=$(echo "$RES" | cut -dx -f1)
RES_H=$(echo "$RES" | cut -dx -f2)
MODEL="$ROOT_DIR/models/openvino_ir/FSRCNN_x${SCALE}.xml"
RUN_ID="hybrid_$(date +%Y%m%dT%H%M%S)"
OUT_DIR="$RESULTS/$RUN_ID"
mkdir -p "$OUT_DIR"

NV=/home/ogg/.local/lib/python3.13/site-packages/nvidia
export LD_LIBRARY_PATH="$NV/cublas/lib:$NV/cudnn/lib:$NV/cuda_runtime/lib:$NV/cufft/lib:$NV/curand/lib:$NV/cusolver/lib:$NV/cusparse/lib:$NV/nvjitlink/lib:$NV/cuda_nvrtc/lib:$NV/nccl/lib:$NV/cuda_cupti/lib:${LD_LIBRARY_PATH:-}"

WRAPPER="$ROOT_DIR/wrapper_swapbuffers_shm.so"
if [[ ! -f "$WRAPPER" ]]; then
  echo "ERROR: $WRAPPER not found. Build it first: bash build.sh"
  exit 1
fi
if [[ ! -f "$MODEL" ]]; then
  echo "ERROR: $MODEL not found. Run: ovc models/FSRCNN_x${SCALE}.pb --output_model models/openvino_ir/FSRCNN_x${SCALE}"
  exit 1
fi

echo "=== Hybrid Test: $RUN_ID ==="
echo "    Scale    : x${SCALE}"
echo "    Game res : ${RES_W}x${RES_H}  →  SR output: $((RES_W*SCALE))x$((RES_H*SCALE))"
echo "    Frames   : $FRAMES"
echo "    Model    : $MODEL"
echo "    Out dir  : $OUT_DIR"
echo ""

# ── Step 1: Start game (real or simulated) ────────────────────────────────────
GAME_PID=""

if [[ "$SIMULATE" -eq 1 ]]; then
  echo "[1/3] Starting game SIMULATOR (using mine.png at ${RES}) ..."
  python3 "$SCRIPT_DIR/simulate_game.py" \
    --source "$ROOT_DIR/mine.png" \
    --res "$RES" \
    --fps 60 \
    --loop \
    --max_frames $((FRAMES * 3)) \
    > "$OUT_DIR/simulator.log" 2>&1 &
  GAME_PID=$!
  echo "      Simulator PID: $GAME_PID"
  sleep 2

else
  echo "[1/3] Launch Minecraft with LD_PRELOAD wrapper."
  echo ""
  echo "  Set game resolution to ${RES_W}x${RES_H}, then start Minecraft with:"
  echo ""
  echo "    LD_PRELOAD=$WRAPPER minecraft-launcher"
  echo ""
  echo "  (Or add LD_PRELOAD=$WRAPPER to the launcher's JVM wrapper script)"
  echo ""
  echo "  Press ENTER when Minecraft is running and in-game ..."
  read -r
fi

# ── Step 2: Capture + SR pipeline ────────────────────────────────────────────
echo "[2/3] Running hybrid SR pipeline (iGPU, OpenVINO GPU) ..."
python3 "$SCRIPT_DIR/hybrid_pipeline.py" \
  --model "$MODEL" \
  --scale "$SCALE" \
  --device GPU \
  --max_frames "$FRAMES" \
  --out_dir "$OUT_DIR" \
  --save_lowres \
  $DISPLAY_FLAG \
  --shm_timeout 120

PIPELINE_EXIT=$?

# Stop simulator if running
if [[ -n "$GAME_PID" ]]; then
  kill "$GAME_PID" 2>/dev/null || true
fi

if [[ "$PIPELINE_EXIT" -ne 0 ]]; then
  echo "ERROR: hybrid_pipeline.py failed (exit $PIPELINE_EXIT)"
  exit 1
fi

echo ""
echo "[3/3] Computing metrics ..."

if [[ "$NO_COMPARE" -eq 0 ]]; then
  python3 "$SCRIPT_DIR/compare_frames.py" \
    --hybrid   "$OUT_DIR/hybrid_frames" \
    --bicubic  "$OUT_DIR/bicubic_frames" \
    --out_csv  "$OUT_DIR/comparison_metrics.csv" \
    --save_diff_images "$OUT_DIR/comparison_images"
fi

echo ""
echo "=== Test complete: $RUN_ID ==="
echo "  Pipeline stats : $OUT_DIR/pipeline_stats.txt"
echo "  Metrics CSV    : $OUT_DIR/comparison_metrics.csv"
echo "  Hybrid frames  : $OUT_DIR/hybrid_frames/"
echo "  Comparison imgs: $OUT_DIR/comparison_images/"
if [[ -f "$OUT_DIR/pipeline_stats.txt" ]]; then
  echo ""
  cat "$OUT_DIR/pipeline_stats.txt"
fi
