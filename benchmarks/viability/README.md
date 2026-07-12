# benchmarks/viability/: estudio de viabilidad (Fase 1)

Matriz sistemática de benchmarks que mide la viabilidad de cada modelo de
superresolución en cada dispositivo/backend. Es el estudio que se presentó al
tutor (resultados resumidos en `../../results/viability_submission/`).

Importado desde el repo TFG_CODE.

## Metodología

580 mediciones combinando:
- **6 dispositivos**: CPU (OpenCV DNN), CPU (OpenVINO), iGPU (OpenCL), iGPU
  (OpenVINO), dGPU (OpenCL), dGPU (CUDA).
- **6 modelos**: FSRCNN ×2/×3/×4, RealESRGAN ×4, super-resolution-10,
  single-image-super-resolution-1032.
- **N resoluciones** de entrada por modelo (FSRCNN 128×72 → 1920×1080;
  ONNX entrada fija 224×224).
- **4 estados de carga**: idle, CPU stress, iGPU stress, dGPU stress.

El modelo se mide **fuera de la arquitectura** (se le pasan imágenes
directamente) para aislar la latencia de inferencia.

## Scripts

| Archivo | Qué hace |
|---|---|
| `benchmark_standalone.py` | Núcleo: mide un modelo en un dispositivo a una resolución (warmup + iters), saca latencia p50/p90/p99 y FPS. |
| `run_viability_matrix.sh` | Lanza la matriz completa (dispositivos × modelos × resoluciones × cargas), gestionando los stressors entre estados. |
| `run_fsrcnn_ir_matrix.sh` | Matriz específica de FSRCNN convertido a OpenVINO IR (la configuración ganadora: iGPU OpenVINO + FSRCNN IR flexible). |
| `run_quality_showcase.sh` | Genera imágenes comparativas + PSNR contra bicúbico. |
| `analyze_viability_tfg.py` | Procesa los CSV → gráficas + tablas LaTeX + resumen. |
| `stressors/` | `igpu_stress.py`, `dgpu_stress.py`: saturan un dispositivo para simular el juego ocupando recursos. |

## Hallazgo clave

Solo **dGPU CUDA** e **iGPU OpenVINO** son viables a 60 FPS. La conversión de
FSRCNN a OpenVINO IR elimina el límite de entrada fija (224×224) de los
modelos ONNX y multiplica los FPS frente a OpenCV DNN (mismo modelo, mismos
pesos, misma calidad). Decisión adoptada: **iGPU OpenVINO + FSRCNN IR**.

## Resultados

CSVs en `results/` (este directorio). El subconjunto curado para el tutor
(gráficas, comparativas, resúmenes) está en
`../../results/viability_submission/`. Los frames crudos (~1 GB) no se
versionan.
