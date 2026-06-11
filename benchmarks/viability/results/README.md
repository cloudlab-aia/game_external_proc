# Viability Benchmark Results

## Overview

**What was tested:** AI super-resolution inference performance across 6 computational devices (CPU, integrated GPU, discrete GPU) and 3 backend frameworks (OpenCV, OpenVINO, CUDA). Tested on 6 model architectures (FSRCNN x2/x3/x4, RealESRGAN, super-resolution-10) at 10 input resolutions (128×72 to 1920×1080) under 4 load conditions (idle, CPU load, iGPU load, dGPU load).

**When tested:** 2026-04-23 to 2026-04-24

**Hardware used:**
- **CPU:** Intel Core Ultra 7 265K (12 cores)
- **Integrated GPU:** Intel Arc Graphics (iGPU, OpenCL backend)
- **Discrete GPU:** NVIDIA GeForce RTX 5060 (OpenCL and CUDA backends)

**Total runs:** 375 (6 devices × 3 models × 10 resolutions × ~2 load conditions, plus ONNX models)

## Data Sources

**CSV files:**
- `viability_results.csv` — Raw benchmark data (375 rows, 22 columns)
- `full_stats.csv` — Device-model-resolution combinations with viability flags
- `summary_by_device.csv` — Per-device summary statistics
- `ranking_idle.csv` — Model rankings by performance at each resolution (idle state)

**Summary reports:**
- `viability_summary.txt` — Human-readable Spanish summary (throughput, degradation, viable combos)

**Visualization:**
- `input_frame_320x180.png` — Input frame reference
- `sample_outputs/` — Example super-resolution outputs

## Key Findings

**CPU_OCV (OpenCV backend):**
Real-time (≥30 fps) only at 256×144 and smaller. Viable for small game UI overlays; best CPU alternative among frameworks.

**iGPU_OCL (Intel integrated GPU, OpenCL):**
Severe dispatch overhead limits only 1 viable resolution (128×72). Consistent across load states but incompatible with modern gaming resolutions. Worse than CPU for most cases.

**dGPU_OCL (NVIDIA RTX 5060, OpenCL):**
High variance under GPU load and launch latency issues. Unreliable for real-time; viable only at very small inputs despite theoretical bandwidth.

**dGPU_CUDA (NVIDIA RTX 5060, CUDA):**
Dominates all resolutions with 895–986 fps at 224×224 (ONNX models). Zero viable combos with older TensorFlow models but exceeds requirements for modern DL frameworks.

**iGPU_OV (Intel iGPU via OpenVINO):**
336 fps at 224×224 ONNX; consistent performance across load states. Viable for energy-constrained scenarios.

**CPU_OV (OpenVINO CPU):**
88 fps at 224×224; competitive with iGPU_OV for small inputs; CPU-backend portability advantage.

## File Organization

```
results/
├── README.md                          (this file)
├── RESULTS_SUMMARY.md                 (tables: viable combos, degradation, rankings, failures)
├── INTERPRETATION.md                  (technical analysis and recommendations)
├── DATA_DICT.md                       (column definitions and abbreviations)
├── viability_results.csv              (raw benchmark data)
├── full_stats.csv                     (per-combination viability flags)
├── summary_by_device.csv              (device-level statistics)
├── ranking_idle.csv                   (model performance ranking)
├── viability_summary.txt              (Spanish summary)
├── input_frame_320x180.png            (reference frame)
└── sample_outputs/                    (upsampled images)
```

## How to Reproduce

Run the viability benchmark from the project root:

```bash
cd /home/ogg/Desktop/TFG_CODE/viability
python viability_benchmark.py --devices cpu_ocv igpu_ocl dgpu_ocl dgpu_cuda cpu_ov igpu_ov \
  --models FSRCNN_x2.pb FSRCNN_x3.pb FSRCNN_x4.pb RealESRGAN_x4.onnx super-resolution-10.onnx \
  --resolutions 128x72 256x144 320x180 480x270 640x360 640x480 800x600 960x540 1280x720 1920x1080 \
  --load-conditions idle cpu igpu dgpu \
  --output-dir results/
```

Results will be written to `viability_results.csv` with summary statistics in `summary_by_device.csv`.
