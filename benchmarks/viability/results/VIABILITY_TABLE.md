# Tabla de Viabilidad — Upscaling AI en Tiempo Real

**Umbral viable:** ≥30 FPS | **Marginal:** 15–29 FPS | **No viable:** <15 FPS
**Métrica calidad:** PSNR vs bicubic (frames sintéticos `mixed`). SSIM entre paréntesis.
**Stress tests:** degradación relativa respecto a idle en mismo combo.

---
## FSRCNN_x2.pb
_×2 → salida duplica resolución_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OCV | 128×72 | 256×144 | 660.2 | 1.5 | 37.0 (0.976) | ✓ VIABLE | CPU-str: 536 (-19%) | iGPU-str: 689 (+4%) | dGPU-str: 680 (+3%) |
| CPU_OCV | 1280×720 | 2560×1440 | 1.0 | 1000.0 | 45.8 (0.995) | ✗ NO | CPU-str: 1 (+24%) | iGPU-str: 1 (+3%) | dGPU-str: 1 (-2%) |
| CPU_OCV | 1920×1080 | 3840×2160 | 0.4 | 2272.7 | 47.0 (0.996) | ✗ NO | CPU-str: 0 (-7%) | iGPU-str: 0 (+5%) | dGPU-str: 0 (+0%) |
| CPU_OCV | 256×144 | 512×288 | 115.5 | 8.7 | 39.9 (0.984) | ✓ VIABLE | CPU-str: 54 (-53%) | iGPU-str: 144 (+25%) | dGPU-str: 128 (+11%) |
| CPU_OCV | 320×180 | 640×360 | 55.9 | 17.9 | 40.8 (0.986) | ✓ VIABLE | CPU-str: 26 (-54%) | iGPU-str: 67 (+20%) | dGPU-str: 64 (+15%) |
| CPU_OCV | 480×270 | 960×540 | 16.6 | 60.4 | 42.4 (0.990) | ~ MARGINAL | CPU-str: 9 (-45%) | iGPU-str: 19 (+15%) | dGPU-str: 18 (+9%) |
| CPU_OCV | 640×360 | 1280×720 | 5.4 | 184.5 | 43.5 (0.992) | ✗ NO | CPU-str: 4 (-32%) | iGPU-str: 6 (+6%) | dGPU-str: 6 (+3%) |
| CPU_OCV | 640×480 | 1280×960 | 3.9 | 253.8 | 43.8 (0.993) | ✗ NO | CPU-str: 3 (-25%) | iGPU-str: 4 (+4%) | dGPU-str: 4 (+1%) |
| CPU_OCV | 800×600 | 1600×1200 | 2.4 | 413.2 | 44.6 (0.994) | ✗ NO | CPU-str: 2 (-33%) | iGPU-str: 3 (+5%) | dGPU-str: 2 (+2%) |
| CPU_OCV | 960×540 | 1920×1080 | 2.2 | 452.5 | 44.9 (0.994) | ✗ NO | CPU-str: 2 (-32%) | iGPU-str: 2 (+6%) | dGPU-str: 2 (+4%) |
| iGPU_OCL | 128×72 | 256×144 | 95.2 | 10.5 | 37.0 (0.976) | ✓ VIABLE | CPU-str: 58 (-39%) | iGPU-str: 99 (+4%) | dGPU-str: 86 (-10%) |
| iGPU_OCL | 1280×720 | 2560×1440 | 1.4 | 709.2 | 45.8 (0.995) | ✗ NO | CPU-str: 1 (-26%) | iGPU-str: 1 (-4%) | dGPU-str: 1 (-9%) |
| iGPU_OCL | 1920×1080 | 3840×2160 | 0.6 | 1612.9 | 47.0 (0.996) | ✗ NO | CPU-str: 0 (-24%) | iGPU-str: 0 (-31%) | dGPU-str: 1 (-6%) |
| iGPU_OCL | 256×144 | 512×288 | 29.2 | 34.3 | 39.9 (0.984) | ~ MARGINAL | CPU-str: 28 (-4%) | iGPU-str: 32 (+8%) | dGPU-str: 28 (-5%) |
| iGPU_OCL | 320×180 | 640×360 | 20.7 | 48.4 | 40.8 (0.986) | ~ MARGINAL | CPU-str: 15 (-26%) | iGPU-str: 22 (+6%) | dGPU-str: 19 (-10%) |
| iGPU_OCL | 480×270 | 960×540 | 9.7 | 103.1 | 42.4 (0.990) | ✗ NO | CPU-str: 7 (-26%) | iGPU-str: 10 (+5%) | dGPU-str: 9 (-5%) |
| iGPU_OCL | 640×360 | 1280×720 | 5.4 | 184.5 | 43.5 (0.992) | ✗ NO | CPU-str: 5 (-9%) | iGPU-str: 6 (+7%) | dGPU-str: 5 (-10%) |
| iGPU_OCL | 640×480 | 1280×960 | 4.0 | 247.5 | 43.8 (0.993) | ✗ NO | CPU-str: 3 (-23%) | iGPU-str: 4 (+9%) | dGPU-str: 4 (-4%) |
| iGPU_OCL | 800×600 | 1600×1200 | 2.6 | 389.1 | 44.6 (0.994) | ✗ NO | CPU-str: 2 (-18%) | iGPU-str: 3 (+11%) | dGPU-str: 3 (-2%) |
| iGPU_OCL | 960×540 | 1920×1080 | 2.5 | 403.2 | 44.9 (0.994) | ✗ NO | CPU-str: 2 (-24%) | iGPU-str: 3 (+6%) | dGPU-str: 2 (-4%) |
| dGPU_OCL | 128×72 | 256×144 | 138.4 | 7.2 | 37.0 (0.976) | ✓ VIABLE | CPU-str: 144 (+4%) | iGPU-str: 91 (-34%) | dGPU-str: 83 (-40%) |
| dGPU_OCL | 1280×720 | 2560×1440 | 1.6 | 628.9 | 45.8 (0.995) | ✗ NO | CPU-str: 2 (+7%) | iGPU-str: 1 (-52%) | dGPU-str: 1 (-13%) |
| dGPU_OCL | 1920×1080 | 3840×2160 | 0.7 | 1408.5 | 47.0 (0.996) | ✗ NO | CPU-str: 1 (+4%) | iGPU-str: 0 (-52%) | dGPU-str: 1 (-15%) |
| dGPU_OCL | 256×144 | 512×288 | 39.5 | 25.3 | 39.9 (0.984) | ✓ VIABLE | CPU-str: 42 (+6%) | iGPU-str: 28 (-30%) | dGPU-str: 36 (-9%) |
| dGPU_OCL | 320×180 | 640×360 | 25.6 | 39.1 | 40.8 (0.986) | ~ MARGINAL | CPU-str: 9 (-65%) | iGPU-str: 14 (-47%) | dGPU-str: 23 (-10%) |
| dGPU_OCL | 480×270 | 960×540 | 11.0 | 91.2 | 42.4 (0.990) | ✗ NO | CPU-str: 12 (+12%) | iGPU-str: 7 (-35%) | dGPU-str: 11 (-4%) |
| dGPU_OCL | 640×360 | 1280×720 | 6.6 | 150.8 | 43.5 (0.992) | ✗ NO | CPU-str: 7 (+2%) | iGPU-str: 6 (-12%) | dGPU-str: 6 (-13%) |
| dGPU_OCL | 640×480 | 1280×960 | 5.0 | 199.2 | 43.8 (0.993) | ✗ NO | CPU-str: 5 (+0%) | iGPU-str: 2 (-52%) | dGPU-str: 4 (-15%) |
| dGPU_OCL | 800×600 | 1600×1200 | 3.0 | 327.9 | 44.6 (0.994) | ✗ NO | CPU-str: 3 (+5%) | iGPU-str: 1 (-52%) | dGPU-str: 3 (-11%) |
| dGPU_OCL | 960×540 | 1920×1080 | 2.8 | 357.1 | 44.9 (0.994) | ✗ NO | CPU-str: 3 (+8%) | iGPU-str: 1 (-55%) | dGPU-str: 3 (-9%) |

---
## FSRCNN_x3.pb
_×3 → salida triplica resolución_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OCV | 128×72 | 384×216 | 596.4 | 1.7 | 35.0 (0.971) | ✓ VIABLE | CPU-str: 429 (-28%) | iGPU-str: 635 (+6%) | dGPU-str: 558 (-6%) |
| CPU_OCV | 1280×720 | 3840×2160 | 1.2 | 854.7 | 43.1 (0.992) | ✗ NO | CPU-str: 1 (-16%) | iGPU-str: 1 (+4%) | dGPU-str: 1 (-1%) |
| CPU_OCV | 256×144 | 768×432 | 115.0 | 8.7 | 37.9 (0.981) | ✓ VIABLE | CPU-str: 74 (-36%) | iGPU-str: 152 (+32%) | dGPU-str: 132 (+14%) |
| CPU_OCV | 320×180 | 960×540 | 55.0 | 18.2 | 38.8 (0.983) | ✓ VIABLE | CPU-str: 29 (-48%) | iGPU-str: 64 (+17%) | dGPU-str: 61 (+11%) |
| CPU_OCV | 480×270 | 1440×810 | 16.5 | 60.7 | 40.2 (0.987) | ~ MARGINAL | CPU-str: 9 (-44%) | iGPU-str: 19 (+12%) | dGPU-str: 15 (-10%) |
| CPU_OCV | 640×360 | 1920×1080 | 7.7 | 130.2 | 41.2 (0.989) | ✗ NO | CPU-str: 4 (-49%) | iGPU-str: 9 (+16%) | dGPU-str: 8 (+5%) |
| CPU_OCV | 640×480 | 1920×1440 | 5.6 | 179.5 | 41.5 (0.989) | ✗ NO | CPU-str: 3 (-50%) | iGPU-str: 6 (+14%) | dGPU-str: 6 (+5%) |
| CPU_OCV | 800×600 | 2400×1800 | 2.3 | 434.8 | 42.2 (0.991) | ✗ NO | CPU-str: 2 (-28%) | iGPU-str: 2 (+5%) | dGPU-str: 2 (+2%) |
| CPU_OCV | 960×540 | 2880×1620 | 2.1 | 471.7 | 42.4 (0.991) | ✗ NO | CPU-str: 3 (+21%) | iGPU-str: 2 (+5%) | dGPU-str: 2 (+0%) |
| iGPU_OCL | 128×72 | 384×216 | 94.0 | 10.6 | 35.0 (0.971) | ✓ VIABLE | CPU-str: 62 (-34%) | iGPU-str: 7 (-93%) | dGPU-str: 88 (-6%) |
| iGPU_OCL | 1280×720 | 3840×2160 | 1.3 | 781.2 | 43.1 (0.992) | ✗ NO | CPU-str: 1 (+5%) | iGPU-str: 1 (-30%) | dGPU-str: 1 (-4%) |
| iGPU_OCL | 256×144 | 768×432 | 29.5 | 33.9 | 37.9 (0.981) | ~ MARGINAL | CPU-str: 13 (-55%) | iGPU-str: 25 (-16%) | dGPU-str: 26 (-12%) |
| iGPU_OCL | 320×180 | 960×540 | 20.8 | 48.0 | 38.8 (0.983) | ~ MARGINAL | CPU-str: 14 (-35%) | iGPU-str: 9 (-55%) | dGPU-str: 19 (-10%) |
| iGPU_OCL | 480×270 | 1440×810 | 9.7 | 103.3 | 40.2 (0.987) | ✗ NO | CPU-str: 6 (-38%) | iGPU-str: 4 (-54%) | dGPU-str: 9 (-9%) |
| iGPU_OCL | 640×360 | 1920×1080 | 5.1 | 196.9 | 41.2 (0.989) | ✗ NO | CPU-str: 4 (-26%) | iGPU-str: 3 (-43%) | dGPU-str: 5 (-6%) |
| iGPU_OCL | 640×480 | 1920×1440 | 4.0 | 252.5 | 41.5 (0.989) | ✗ NO | CPU-str: 4 (-11%) | iGPU-str: 2 (-40%) | dGPU-str: 4 (-8%) |
| iGPU_OCL | 800×600 | 2400×1800 | 2.5 | 408.2 | 42.2 (0.991) | ✗ NO | CPU-str: 2 (-23%) | iGPU-str: 2 (-36%) | dGPU-str: 2 (-4%) |
| iGPU_OCL | 960×540 | 2880×1620 | 2.4 | 416.7 | 42.4 (0.991) | ✗ NO | CPU-str: 2 (-28%) | iGPU-str: 2 (-28%) | dGPU-str: 2 (-10%) |
| dGPU_OCL | 128×72 | 384×216 | 141.5 | 7.1 | 35.0 (0.971) | ✓ VIABLE | CPU-str: 137 (-3%) | iGPU-str: 133 (-6%) | dGPU-str: 83 (-41%) |
| dGPU_OCL | 1280×720 | 3840×2160 | 1.4 | 724.6 | 43.1 (0.992) | ✗ NO | CPU-str: 2 (+12%) | iGPU-str: 1 (+5%) | dGPU-str: 1 (-8%) |
| dGPU_OCL | 256×144 | 768×432 | 37.8 | 26.5 | 37.9 (0.981) | ✓ VIABLE | CPU-str: 41 (+8%) | iGPU-str: 18 (-52%) | dGPU-str: 33 (-13%) |
| dGPU_OCL | 320×180 | 960×540 | 24.1 | 41.6 | 38.8 (0.983) | ~ MARGINAL | CPU-str: 26 (+10%) | iGPU-str: 11 (-53%) | dGPU-str: 22 (-10%) |
| dGPU_OCL | 480×270 | 1440×810 | 11.4 | 87.3 | 40.2 (0.987) | ✗ NO | CPU-str: 12 (+2%) | iGPU-str: 5 (-56%) | dGPU-str: 10 (-14%) |
| dGPU_OCL | 640×360 | 1920×1080 | 6.2 | 162.3 | 41.2 (0.989) | ✗ NO | CPU-str: 7 (+9%) | iGPU-str: 3 (-45%) | dGPU-str: 5 (-11%) |
| dGPU_OCL | 640×480 | 1920×1440 | 4.3 | 233.1 | 41.5 (0.989) | ✗ NO | CPU-str: 5 (+10%) | iGPU-str: 2 (-48%) | dGPU-str: 4 (-5%) |
| dGPU_OCL | 800×600 | 2400×1800 | 2.7 | 370.4 | 42.2 (0.991) | ✗ NO | CPU-str: 3 (+13%) | iGPU-str: 3 (+3%) | dGPU-str: 2 (-8%) |
| dGPU_OCL | 960×540 | 2880×1620 | 2.5 | 403.2 | 42.4 (0.991) | ✗ NO | CPU-str: 3 (+13%) | iGPU-str: 2 (+1%) | dGPU-str: 2 (-6%) |

---
## FSRCNN_x4.pb
_×4 → salida cuadruplica resolución_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OCV | 128×72 | 512×288 | 507.2 | 2.0 | 35.4 (0.968) | ✓ VIABLE | CPU-str: 388 (-23%) | iGPU-str: 530 (+5%) | dGPU-str: 496 (-2%) |
| CPU_OCV | 256×144 | 1024×576 | 95.9 | 10.4 | 38.6 (0.982) | ✓ VIABLE | CPU-str: 78 (-18%) | iGPU-str: 109 (+14%) | dGPU-str: 98 (+2%) |
| CPU_OCV | 320×180 | 1280×720 | 19.1 | 52.3 | 39.5 (0.985) | ~ MARGINAL | CPU-str: 39 (+103%) | iGPU-str: 56 (+194%) | dGPU-str: 54 (+182%) |
| CPU_OCV | 480×270 | 1920×1080 | 15.5 | 64.7 | 41.1 (0.989) | ~ MARGINAL | CPU-str: 11 (-28%) | iGPU-str: 18 (+14%) | dGPU-str: 17 (+8%) |
| CPU_OCV | 640×360 | 2560×1440 | 6.8 | 148.1 | 42.2 (0.991) | ✗ NO | CPU-str: 4 (-45%) | iGPU-str: 8 (+12%) | dGPU-str: 7 (-1%) |
| CPU_OCV | 640×480 | 2560×1920 | 4.9 | 204.1 | 42.7 (0.991) | ✗ NO | CPU-str: 3 (-34%) | iGPU-str: 6 (+16%) | dGPU-str: 5 (-7%) |
| CPU_OCV | 800×600 | 3200×2400 | 3.0 | 334.4 | — | ✗ NO | CPU-str: 3 (-5%) |
| CPU_OCV | 960×540 | 3840×2160 | 2.7 | 366.3 | 43.6 (0.992) | ✗ NO | CPU-str: 2 (-19%) | iGPU-str: 3 (+16%) | dGPU-str: 3 (+0%) |
| iGPU_OCL | 128×72 | 512×288 | 87.7 | 11.4 | 35.4 (0.968) | ✓ VIABLE | CPU-str: 86 (-2%) | iGPU-str: 21 (-76%) | dGPU-str: 74 (-15%) |
| iGPU_OCL | 256×144 | 1024×576 | 27.1 | 36.9 | 38.6 (0.982) | ~ MARGINAL | CPU-str: 28 (+3%) | iGPU-str: 11 (-61%) | dGPU-str: 25 (-6%) |
| iGPU_OCL | 320×180 | 1280×720 | 18.8 | 53.2 | 39.5 (0.985) | ~ MARGINAL | CPU-str: 20 (+7%) | iGPU-str: 18 (-4%) | dGPU-str: 18 (-3%) |
| iGPU_OCL | 480×270 | 1920×1080 | 8.9 | 112.9 | 41.1 (0.989) | ✗ NO | CPU-str: 9 (+7%) | iGPU-str: 5 (-41%) | dGPU-str: 8 (-8%) |
| iGPU_OCL | 640×360 | 2560×1440 | 4.8 | 210.5 | 42.2 (0.991) | ✗ NO | CPU-str: 5 (+4%) | iGPU-str: 3 (-37%) | dGPU-str: 4 (-7%) |
| iGPU_OCL | 640×480 | 2560×1920 | 3.4 | 296.7 | 42.7 (0.991) | ✗ NO | CPU-str: 4 (+9%) | iGPU-str: 3 (-2%) | dGPU-str: 3 (+1%) |
| iGPU_OCL | 800×600 | 3200×2400 | 2.2 | 448.4 | — | ✗ NO | CPU-str: 2 (+8%) |
| iGPU_OCL | 960×540 | 3840×2160 | 2.1 | 471.7 | 43.6 (0.992) | ✗ NO | CPU-str: 2 (+5%) | iGPU-str: 2 (-25%) | dGPU-str: 2 (-5%) |
| dGPU_OCL | 128×72 | 512×288 | 123.6 | 8.1 | 35.4 (0.968) | ✓ VIABLE | CPU-str: 119 (-4%) | iGPU-str: 126 (+2%) | dGPU-str: 81 (-35%) |
| dGPU_OCL | 256×144 | 1024×576 | 38.7 | 25.9 | 38.6 (0.982) | ✓ VIABLE | CPU-str: 38 (-3%) | iGPU-str: 37 (-5%) | dGPU-str: 32 (-18%) |
| dGPU_OCL | 320×180 | 1280×720 | 24.9 | 40.2 | 39.5 (0.985) | ~ MARGINAL | CPU-str: 24 (-2%) | iGPU-str: 24 (-5%) | dGPU-str: 21 (-15%) |
| dGPU_OCL | 480×270 | 1920×1080 | 10.9 | 91.6 | 41.1 (0.989) | ✗ NO | CPU-str: 11 (+0%) | iGPU-str: 11 (-3%) | dGPU-str: 9 (-15%) |
| dGPU_OCL | 640×360 | 2560×1440 | 5.5 | 182.8 | 42.2 (0.991) | ✗ NO | CPU-str: 6 (+5%) | iGPU-str: 5 (-2%) | dGPU-str: 5 (-12%) |
| dGPU_OCL | 640×480 | 2560×1920 | 4.2 | 240.4 | 42.7 (0.991) | ✗ NO | CPU-str: 4 (+4%) | iGPU-str: 4 (-3%) | dGPU-str: 4 (-10%) |
| dGPU_OCL | 800×600 | 3200×2400 | 2.6 | 377.4 | — | ✗ NO | CPU-str: 3 (+4%) |
| dGPU_OCL | 960×540 | 3840×2160 | 2.5 | 408.2 | 43.6 (0.992) | ✗ NO | CPU-str: 3 (+5%) | iGPU-str: 2 (-7%) | dGPU-str: 2 (-18%) |

---
## super-resolution-10.onnx
_×3 fijo (entrada 224×224 → salida 672×672)_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OV | 224×224 | 672×672 | 87.9 | 11.4 | 31.9 (0.940) | ✓ VIABLE | CPU-str: 56 (-37%) | iGPU-str: 87 (-1%) | dGPU-str: 101 (+15%) |
| iGPU_OV | 224×224 | 672×672 | 335.7 | 3.0 | 31.9 (0.939) | ✓ VIABLE | CPU-str: 300 (-11%) | iGPU-str: 332 (-1%) | dGPU-str: 314 (-6%) |
| dGPU_CUDA | 224×224 | 672×672 | 894.9 | 1.1 | 31.9 (0.940) | ✓ VIABLE | CPU-str: 1016 (+14%) | iGPU-str: 997 (+11%) | dGPU-str: 621 (-31%) |

---
## RealESRGAN_x4.onnx
_×3 fijo (entrada 224×224 → salida 672×672)_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OV | 224×224 | 672×672 | 78.0 | 12.8 | 31.9 (0.940) | ✓ VIABLE | CPU-str: 57 (-26%) | iGPU-str: 87 (+12%) | dGPU-str: 117 (+50%) |
| iGPU_OV | 224×224 | 672×672 | 334.7 | 3.0 | 31.9 (0.939) | ✓ VIABLE | CPU-str: 304 (-9%) | iGPU-str: 335 (+0%) | dGPU-str: 301 (-10%) |
| dGPU_CUDA | 224×224 | 672×672 | 986.0 | 1.0 | 31.9 (0.940) | ✓ VIABLE | CPU-str: 1032 (+5%) | iGPU-str: 969 (-2%) | dGPU-str: 622 (-37%) |

---
## single-image-super-resolution-1032.xml
_×4 fijo (entrada 480×270 → salida 1920×1080)_

| Device | Entrada | Salida | FPS idle | Lat ms | PSNR dB (SSIM) | Viabilidad | Stress (FPS, Δ%) |
|--------|---------|--------|----------|--------|----------------|------------|-----------------|
| CPU_OV | 480×270 | 1920×1080 | 15.7 | 63.9 | 45.0 (0.995) | ~ MARGINAL | CPU-str: 11 (-27%) | iGPU-str: 15 (-4%) | dGPU-str: 16 (+3%) |
| iGPU_OV | 320×180 | 1920×1080 | 8.6 | 116.9 | — | ✗ NO | — |
| iGPU_OV | 480×270 | 1920×1080 | 29.1 | 34.3 | 45.0 (0.995) | ~ MARGINAL | CPU-str: 29 (-1%) | iGPU-str: 28 (-2%) | dGPU-str: 26 (-12%) |

---
## Resumen: Combos viables por resolución de SALIDA

| Resolución salida | Combos ≥30 FPS | Mejor opción |
|-------------------|----------------|-------------|
| 256×144 | 3 | CPU_OCV / FSRCNN_x2.pb (660 FPS) |
| 384×216 | 3 | CPU_OCV / FSRCNN_x3.pb (596 FPS) |
| 512×288 | 5 | CPU_OCV / FSRCNN_x4.pb (507 FPS) |
| 640×360 | 1 | CPU_OCV / FSRCNN_x2.pb (56 FPS) |
| 672×672 | 6 | dGPU_CUDA / RealESRGAN_x4.onnx (986 FPS) |
| 768×432 | 2 | CPU_OCV / FSRCNN_x3.pb (115 FPS) |
| 960×540 | 1 | CPU_OCV / FSRCNN_x3.pb (55 FPS) |
| 1024×576 | 2 | CPU_OCV / FSRCNN_x4.pb (96 FPS) |

---
## Notas de arquitectura

- **FSRCNN (.pb):** resolución flexible. Backend OpenCV DNN. iGPU_OCL y dGPU_OCL usan OpenCL — verificado por `active_backend_name` (Intel Graphics / NVIDIA RTX 5060).
- **super-resolution-10 / RealESRGAN (.onnx):** entrada hardcoded 224×224. OpenVINO falla con reshape en otras resoluciones (7.9% failures totales). dGPU_CUDA usa ONNX Runtime con CUDAExecutionProvider.
- **single-image-super-resolution-1032 (.xml):** modelo con 2 entradas (LR 480×270 + HR bicúbico 1920×1080). Solo CPU_OV e iGPU_OV.
- **dGPU_OCL vs dGPU_CUDA:** mismo hardware (RTX 5060) pero backend distinto. OpenCL 5-10× más lento que CUDA para estos modelos.