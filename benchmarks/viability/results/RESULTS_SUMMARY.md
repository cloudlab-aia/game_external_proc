# Viability Results Summary

## Real-Time Viable Combinations (≥30 fps, p50 < 33.3ms)

### CPU_OCV

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| FSRCNN_x2 | 128×72 | 1.52 | 660.2 | ✓ 60fps |
| FSRCNN_x2 | 256×144 | 8.66 | 115.5 | ✓ 60fps |
| FSRCNN_x2 | 320×180 | 17.89 | 55.9 | ✓ 30fps |
| FSRCNN_x3 | 128×72 | 1.68 | 596.4 | ✓ 60fps |
| FSRCNN_x3 | 256×144 | 8.70 | 114.98 | ✓ 60fps |
| FSRCNN_x3 | 320×180 | 18.20 | 54.95 | ✓ 30fps |
| FSRCNN_x4 | 128×72 | 1.97 | 507.2 | ✓ 60fps |
| FSRCNN_x4 | 256×144 | 10.43 | 95.9 | ✓ 60fps |
| FSRCNN_x4 | 320×180 | 20.44 | 48.92 | ✓ 30fps |
| **Total viable** | — | — | — | **9/27 (33%)** |

### iGPU_OCL

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| FSRCNN_x2 | 128×72 | 10.51 | 95.2 | ✓ 60fps |
| **Total viable** | — | — | — | **1/27 (4%)** |

### dGPU_OCL

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| FSRCNN_x2 | 128×72 | 7.22 | 138.4 | ✓ 60fps |
| FSRCNN_x3 | 128×72 | 7.07 | 141.5 | ✓ 60fps |
| FSRCNN_x4 | 128×72 | 8.09 | 123.6 | ✓ 60fps |
| FSRCNN_x2 | 256×144 | 25.33 | 39.5 | ✓ 30fps |
| FSRCNN_x3 | 256×144 | 26.48 | 37.8 | ✓ 30fps |
| FSRCNN_x4 | 256×144 | 25.86 | 38.7 | ✓ 30fps |
| **Total viable** | — | — | — | **6/27 (22%)** |

### CPU_OV (ONNX models)

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| RealESRGAN_x4 | 224×224 | 11.28 | 88.6 | ✓ 60fps |
| super-resolution-10 | 224×224 | 11.37 | 87.9 | ✓ 60fps |
| **Total viable** | — | — | — | **2/3 (67%)** |

### iGPU_OV (ONNX models)

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| RealESRGAN_x4 | 224×224 | 2.99 | 334.7 | ✓ 60fps |
| super-resolution-10 | 224×224 | 2.98 | 335.7 | ✓ 60fps |
| **Total viable** | — | — | — | **2/3 (67%)** |

### dGPU_CUDA (ONNX models)

| Model | Resolution | p50 (ms) | FPS (p50) | Status |
|-------|-----------|----------|----------|--------|
| RealESRGAN_x4 | 224×224 | 1.01 | 986.0 | ✓ 60fps |
| super-resolution-10 | 224×224 | 1.12 | 894.9 | ✓ 60fps |
| **Total viable** | — | — | — | **2/2 (100%)** |

## Performance Degradation Under Load

Mean percent change in latency (p50) under CPU/iGPU/dGPU load vs. idle state:

| Device | CPU Load | iGPU Load | dGPU Load |
|--------|----------|-----------|-----------|
| CPU_OCV | +10.6% | −0.4% | +8.0% |
| CPU_OV | +49.9% | +2.3% | +9.0% |
| iGPU_OCL | −4.4% | −1.5% | +9.3% |
| iGPU_OV | +7.5% | +1.1% | +13.8% |
| dGPU_OCL | +2.5% | +0.6% | +23.9% |
| dGPU_CUDA | −8.2% | −4.2% | +64.2% |

**Key observation:** dGPU_CUDA shows 64.2% degradation under dGPU load (other GPU jobs competing). dGPU_OCL shows severe interference (23.9%). CPU backends remain stable across all load conditions.

## Model Rankings per Device (Idle, 320×180 resolution)

### CPU_OCV
1. FSRCNN_x2: 55.9 fps
2. FSRCNN_x3: 54.95 fps
3. FSRCNN_x4: 48.92 fps

### iGPU_OCL
1. FSRCNN_x2: 20.67 fps
2. FSRCNN_x3: 20.82 fps
3. FSRCNN_x4: 18.78 fps

### dGPU_OCL
1. FSRCNN_x3: 24.05 fps
2. FSRCNN_x2: 25.56 fps
3. FSRCNN_x4: 24.88 fps

### dGPU_CUDA (224×224, ONNX models only)
1. RealESRGAN_x4: 985.95 fps
2. super-resolution-10: 894.94 fps

### CPU_OV / iGPU_OV (224×224, ONNX models only)
- **CPU_OV:** RealESRGAN_x4 (88.6 fps) = super-resolution-10 (87.9 fps)
- **iGPU_OV:** RealESRGAN_x4 (334.7 fps) = super-resolution-10 (335.7 fps)

## Maximum Viable Resolution by Device (≥60 fps, idle)

| Device | Max Resolution | Model | FPS |
|--------|----------------|-------|-----|
| CPU_OCV | 256×144 | FSRCNN_x2 | 115.5 |
| iGPU_OCL | 128×72 | FSRCNN_x2 | 95.2 |
| dGPU_OCL | 128×72 | FSRCNN_x2 | 138.4 |
| CPU_OV | 224×224 | RealESRGAN_x4 | 88.6 |
| iGPU_OV | 224×224 | super-resolution-10 | 335.7 |
| dGPU_CUDA | 224×224 | RealESRGAN_x4 | 986.0 |

## Failure Analysis

### Category: No viable real-time combination
- **iGPU_OCL with FSRCNN:** OpenCL dispatch overhead + limited compute prevent ≥30 fps except at minimal resolution
- **dGPU_OCL with large inputs:** Kernel launch latency and synchronization overhead dominate computation for inputs >256×144

### Category: Framework mismatch
- **FSRCNN .pb models:** No CUDA backend; only OpenCV (CPU) or OpenCL (GPU)
- **ONNX models:** Only dGPU_CUDA achieves real-time beyond token resolutions; CPU_OV/iGPU_OV viable only at 224×224

### Category: Load interference
- **dGPU_CUDA under dGPU load:** +64.2% latency penalty (worst of all devices). Indicates poor sharing behavior with competing CUDA workloads.
- **dGPU_OCL stability:** High variance (p90/p50 ratio > 2.0 at most resolutions)

### Summary of failures (≥30 fps not achieved)
| Scenario | Count | Root Cause |
|----------|-------|-----------|
| iGPU_OCL + FSRCNN | 26/27 | Dispatch overhead exceeds computation |
| dGPU_OCL + large input | 21/27 | Kernel launch cost dominates |
| CPU_OCV + ≥480×270 | 18/27 | Single-threaded bottleneck (FSRCNN ops serialized) |
| **Total non-viable** | **~130/375** | Mix of architectural and workload mismatches |
