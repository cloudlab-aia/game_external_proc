# Resumen de resultados de viabilidad

## Combinaciones viables en tiempo real (≥30 fps, p50 < 33,3 ms)

### CPU_OCV

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| FSRCNN_x2 | 128×72 | 1.52 | 660.2 | 60 fps |
| FSRCNN_x2 | 256×144 | 8.66 | 115.5 | 60 fps |
| FSRCNN_x2 | 320×180 | 17.89 | 55.9 | 30 fps |
| FSRCNN_x3 | 128×72 | 1.68 | 596.4 | 60 fps |
| FSRCNN_x3 | 256×144 | 8.70 | 114.98 | 60 fps |
| FSRCNN_x3 | 320×180 | 18.20 | 54.95 | 30 fps |
| FSRCNN_x4 | 128×72 | 1.97 | 507.2 | 60 fps |
| FSRCNN_x4 | 256×144 | 10.43 | 95.9 | 60 fps |
| FSRCNN_x4 | 320×180 | 20.44 | 48.92 | 30 fps |
| **Total viable** | - | - | - | **9/27 (33 %)** |

### iGPU_OCL

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| FSRCNN_x2 | 128×72 | 10.51 | 95.2 | 60 fps |
| **Total viable** | - | - | - | **1/27 (4 %)** |

### dGPU_OCL

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| FSRCNN_x2 | 128×72 | 7.22 | 138.4 | 60 fps |
| FSRCNN_x3 | 128×72 | 7.07 | 141.5 | 60 fps |
| FSRCNN_x4 | 128×72 | 8.09 | 123.6 | 60 fps |
| FSRCNN_x2 | 256×144 | 25.33 | 39.5 | 30 fps |
| FSRCNN_x3 | 256×144 | 26.48 | 37.8 | 30 fps |
| FSRCNN_x4 | 256×144 | 25.86 | 38.7 | 30 fps |
| **Total viable** | - | - | - | **6/27 (22 %)** |

### CPU_OV (modelos ONNX)

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| RealESRGAN_x4 | 224×224 | 11.28 | 88.6 | 60 fps |
| super-resolution-10 | 224×224 | 11.37 | 87.9 | 60 fps |
| **Total viable** | - | - | - | **2/3 (67 %)** |

### iGPU_OV (modelos ONNX)

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| RealESRGAN_x4 | 224×224 | 2.99 | 334.7 | 60 fps |
| super-resolution-10 | 224×224 | 2.98 | 335.7 | 60 fps |
| **Total viable** | - | - | - | **2/3 (67 %)** |

### dGPU_CUDA (modelos ONNX)

| Modelo | Resolución | p50 (ms) | FPS (p50) | Nivel |
|--------|-----------|----------|-----------|-------|
| RealESRGAN_x4 | 224×224 | 1.01 | 986.0 | 60 fps |
| super-resolution-10 | 224×224 | 1.12 | 894.9 | 60 fps |
| **Total viable** | - | - | - | **2/2 (100 %)** |

## Degradación de rendimiento bajo carga

Cambio porcentual medio de la latencia (p50) bajo carga de CPU/iGPU/dGPU
respecto al reposo:

| Dispositivo | Carga CPU | Carga iGPU | Carga dGPU |
|-------------|-----------|------------|------------|
| CPU_OCV | +10,6 % | -0,4 % | +8,0 % |
| CPU_OV | +49,9 % | +2,3 % | +9,0 % |
| iGPU_OCL | -4,4 % | -1,5 % | +9,3 % |
| iGPU_OV | +7,5 % | +1,1 % | +13,8 % |
| dGPU_OCL | +2,5 % | +0,6 % | +23,9 % |
| dGPU_CUDA | -8,2 % | -4,2 % | +64,2 % |

**Observación clave:** dGPU_CUDA se degrada un 64,2 % cuando otros trabajos
compiten por la dGPU, y dGPU_OCL sufre una interferencia notable (23,9 %).
Los backends de CPU se mantienen estables en todas las condiciones. Este es
el dato que anticipa la ventaja de la arquitectura híbrida: la inferencia en
la dGPU se hunde justo cuando la dGPU está ocupada renderizando.

## Ranking de modelos por dispositivo (reposo, 320×180)

- **CPU_OCV:** FSRCNN_x2 (55,9 fps) > FSRCNN_x3 (54,95) > FSRCNN_x4 (48,92)
- **iGPU_OCL:** FSRCNN_x3 (20,82 fps) > FSRCNN_x2 (20,67) > FSRCNN_x4 (18,78)
- **dGPU_OCL:** FSRCNN_x2 (25,56 fps) > FSRCNN_x4 (24,88) > FSRCNN_x3 (24,05)
- **dGPU_CUDA (224×224, ONNX):** RealESRGAN_x4 (985,95 fps) > super-resolution-10 (894,94)
- **CPU_OV / iGPU_OV (224×224, ONNX):** ambos modelos prácticamente empatados
  (88,6 y 87,9 fps en CPU; 334,7 y 335,7 fps en iGPU)

## Resolución máxima viable por dispositivo (≥60 fps, reposo)

| Dispositivo | Resolución máx. | Modelo | FPS |
|-------------|-----------------|--------|-----|
| CPU_OCV | 256×144 | FSRCNN_x2 | 115.5 |
| iGPU_OCL | 128×72 | FSRCNN_x2 | 95.2 |
| dGPU_OCL | 128×72 | FSRCNN_x2 | 138.4 |
| CPU_OV | 224×224 | RealESRGAN_x4 | 88.6 |
| iGPU_OV | 224×224 | super-resolution-10 | 335.7 |
| dGPU_CUDA | 224×224 | RealESRGAN_x4 | 986.0 |

## Análisis de los fallos

Combinaciones que no alcanzan tiempo real y su causa:

- **iGPU_OCL con FSRCNN (26/27 no viables):** el sobrecoste de despacho de
  OpenCL más el cómputo limitado impiden los 30 fps salvo a resolución
  mínima.
- **dGPU_OCL con entradas grandes (21/27):** la latencia de lanzamiento de
  kernels y la sincronización dominan sobre el cómputo por encima de
  256×144.
- **CPU_OCV a partir de 480×270 (18/27):** cuello de botella del hilo
  único; las operaciones de FSRCNN se serializan.
- **Modelos .pb:** sin backend CUDA; solo OpenCV (CPU) u OpenCL (GPU).
- **Modelos ONNX:** solo dGPU_CUDA logra tiempo real con holgura;
  CPU_OV/iGPU_OV son viables únicamente a 224×224.
