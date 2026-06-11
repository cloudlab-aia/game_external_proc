# Data Dictionary

## CSV Column Definitions

### viability_results.csv

| Column | Type | Description | Units | Example |
|--------|------|-------------|-------|---------|
| `run_id` | string | Unique benchmark session identifier (timestamp-based) | — | `run_20260423T175951` |
| `timestamp` | ISO-8601 | Exact time of measurement | — | `2026-04-23T17:59:51` |
| `device` | string | Execution device (see Device IDs below) | — | `CPU_OCV`, `dGPU_CUDA` |
| `model` | string | Model file (framework-specific) | — | `FSRCNN_x2.pb`, `super-resolution-10.onnx` |
| `input_w` | integer | Input frame width | pixels | 320 |
| `input_h` | integer | Input frame height | pixels | 180 |
| `output_w` | integer | Output frame width (after upsampling) | pixels | 1280 |
| `output_h` | integer | Output frame height (after upsampling) | pixels | 720 |
| `load_tag` | string | System load condition (see Load States below) | — | `idle`, `cpu`, `igpu`, `dgpu` |
| `warmup` | integer | Inference iterations run before timing (discarded) | count | 5 |
| `iters` | integer | Inference iterations timed | count | 30 |
| `wall_s` | float | Total wall-clock time (all iterations + overhead) | seconds | 3.303 |
| `mean_ms` | float | Mean latency across all iterations | ms | 48.429 |
| `std_ms` | float | Standard deviation of latency | ms | 0.693 |
| `p50_ms` | float | Median (50th percentile) latency | ms | 48.375 |
| `p90_ms` | float | 90th percentile latency (worst-case guarantee for 90% of frames) | ms | 49.209 |
| `p99_ms` | float | 99th percentile latency | ms | 49.844 |
| `min_ms` | float | Minimum observed latency | ms | 47.113 |
| `max_ms` | float | Maximum observed latency | ms | 50.008 |
| `fps_mean` | float | Throughput based on mean latency (1000/mean_ms) | fps | 20.65 |
| `fps_p50` | float | Throughput at median latency (1000/p50_ms) | fps | 20.67 |
| `active_backend_name` | string | Reported GPU vendor/backend (from device query) | — | `Intel(R) Graphics`, `CUDA:RTX5060` |

### full_stats.csv

| Column | Type | Description |
|--------|------|-------------|
| `device` | string | Device ID |
| `model` | string | Model filename |
| `input_w` | integer | Input width |
| `input_h` | integer | Input height |
| `load_tag` | string | Load condition |
| `p50_ms` | float | Median latency |
| `p90_ms` | float | 90th percentile |
| `p99_ms` | float | 99th percentile |
| `mean_ms` | float | Mean latency |
| `fps_p50` | float | Throughput at p50 |
| `degradation_pct` | float | Performance loss under load vs. idle |
| `viable_30fps` | string | ✓ SI / ✗ NO: achieves ≥30 fps (p50 < 33.3 ms) |
| `viable_60fps` | string | ✓ SI / ✗ NO: achieves ≥60 fps (p50 < 16.7 ms) |

### summary_by_device.csv

| Column | Type | Description |
|--------|------|-------------|
| `device` | string | Device ID |
| `load` | string | Load condition |
| `n_cells` | integer | Number of model-resolution combinations tested |
| `mean_of_mean` | float | Average mean latency across all cells |
| `mean_of_p50` | float | Average p50 latency across all cells |
| `mean_of_p90` | float | Average p90 latency across all cells |
| `mean_of_fps_p50` | float | Average fps_p50 across all cells |

### ranking_idle.csv

| Column | Type | Description |
|--------|------|-------------|
| `model` | string | Model filename |
| `input_w` | integer | Input width |
| `input_h` | integer | Input height |
| `rank` | integer | 1 = fastest, 2 = second, 3 = slowest |
| `device` | string | Device ID at this rank |
| `p50_ms` | float | Median latency for this rank |
| `fps_p50` | float | Throughput for this rank |

---

## Device IDs and Abbreviations

| ID | Full Name | Backend | Hardware | Notes |
|----|-----------|---------|----|-------|
| `CPU_OCV` | CPU OpenCV | OpenCV DNN | Intel Core Ultra 7 265K | Fallback CPU implementation, auto-parallelizes |
| `iGPU_OCL` | iGPU OpenCL | OpenCL | Intel Arc (iGPU) | Integrated GPU on Core Ultra 7 265K |
| `dGPU_OCL` | dGPU OpenCL | OpenCL | NVIDIA RTX 5060 | Discrete GPU via OpenCL 1.2 |
| `dGPU_CUDA` | dGPU CUDA | CUDA 12.x | NVIDIA RTX 5060 | Discrete GPU via CUDA (ONNX models only) |
| `CPU_OV` | CPU OpenVINO | OpenVINO (CPU) | Intel Core Ultra 7 265K | ONNX models via OpenVINO runtime |
| `iGPU_OV` | iGPU OpenVINO | OpenVINO (GPU) | Intel Arc (iGPU) | ONNX models via OpenVINO GPU plugin |

---

## Load States

| Tag | Description | How Achieved | Purpose |
|-----|-------------|-------------|---------|
| `idle` | System at rest (no competing workloads) | Benchmark runs alone | Baseline performance measurement |
| `cpu` | CPU contention | 12 threads (100% core usage) running synthetic load | Test robustness to host-side CPU queuing delays |
| `igpu` | iGPU contention | 8×32 grid parallel workload (custom OpenCL kernel) | Test iGPU sharing and memory bank conflicts |
| `dgpu` | dGPU contention | 32×32 grid CUDA kernel or OpenCL workload | Test discrete GPU context switching |

Each load condition replaces the idle workload; measured in separate runs (not concurrent).

---

## Model Abbreviations

| Model | Type | Framework | Input | Output | Notes |
|-------|------|-----------|-------|--------|-------|
| `FSRCNN_x2.pb` | Super-resolution | TensorFlow/Protobuf | Any WxH | 2×W × 2×H | 3-layer CNN, 2× upsampling |
| `FSRCNN_x3.pb` | Super-resolution | TensorFlow/Protobuf | Any WxH | 3×W × 3×H | 3-layer CNN, 3× upsampling |
| `FSRCNN_x4.pb` | Super-resolution | TensorFlow/Protobuf | Any WxH | 4×W × 4×H | 3-layer CNN, 4× upsampling |
| `RealESRGAN_x4.onnx` | Super-resolution | ONNX | 224×224 (fixed) | 896×896 | Real-world upsampling, 4× scale, large model |
| `super-resolution-10.onnx` | Super-resolution | ONNX | 224×224 (fixed) | 672×672 | 3× upsampling, lightweight |
| `single-image-super-resolution-1032.xml` | Super-resolution | OpenVINO IR | 480×270 | 1920×1080 | OpenVINO Intermediate Representation format |

**Note:** .pb (Protobuf) and .xml (OpenVINO IR) models support variable input shapes. .onnx models require 224×224 (hardcoded reshape in inference code). All models output RGB or grayscale; input is assumed single-frame or batch of 1.

---

## Viability Thresholds

| Threshold | Definition | Rationale |
|-----------|-----------|-----------|
| ≥30 fps | `p50_ms < 33.3 ms` | Video game refresh rate (most games run 30+ fps minimum) |
| ≥60 fps | `p50_ms < 16.7 ms` | Modern display refresh rate (1000/60 ≈ 16.67) |
| Real-time | ≥30 fps under idle conditions | Acceptable for interactive applications |

**Note:** Measurements use **p50 (median)**, not mean, because latency distribution is non-normal (right-skewed). p50 is the guarantee for 50% of frames; p90 is the worst-case for 90%.

---

## Derived Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| `fps_p50` | 1000 / p50_ms | Throughput if every frame takes exactly p50 time |
| `degradation_pct` | 100 × (latency_under_load - latency_idle) / latency_idle | Percent slowdown caused by competing workload |
| `viable_30fps` | p50_ms ≤ 33.3 ms | Boolean: can achieve ≥30 fps? |
| `viable_60fps` | p50_ms ≤ 16.7 ms | Boolean: can achieve ≥60 fps? |
| `p90/p50 ratio` | p90_ms / p50_ms | Stability indicator (lower = more consistent) |

---

## Units and Precision

- **Latency:** milliseconds (ms), precision ±0.01 ms
- **FPS:** frames per second, computed as 1000 / latency_ms
- **Throughput:** effective mega-pixels per second: fps × (input_w × input_h × bytes_per_pixel) / 1e6
- **Degradation:** percent (%), relative change
- **Timestamps:** ISO-8601 UTC
- **Resolution:** pixels (width × height)
