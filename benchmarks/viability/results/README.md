# Resultados del benchmark de viabilidad

## Qué se midió

Rendimiento de inferencia de superresolución con IA en 6 configuraciones de
dispositivo (CPU, GPU integrada y GPU dedicada, cada una con sus backends
OpenCV, OpenVINO y CUDA), con 5 modelos (FSRCNN x2/x3/x4, RealESRGAN,
super-resolution-10), 10 resoluciones de entrada (de 128×72 a 1920×1080) y
4 condiciones de carga (reposo, carga de CPU, de iGPU y de dGPU).

**Fechas:** 23 y 24 de abril de 2026

**Hardware:**
- **CPU:** Intel Core Ultra 7 265K
- **GPU integrada:** Intel Graphics (backend OpenCL)
- **GPU dedicada:** NVIDIA GeForce RTX 5060 (backends OpenCL y CUDA)

**Total de ejecuciones:** 375

## Ficheros de datos

**CSV:**
- `viability_results.csv`: datos crudos del benchmark (375 filas, 22 columnas)
- `full_stats.csv`: combinaciones dispositivo-modelo-resolución con sus
  indicadores de viabilidad
- `summary_by_device.csv`: estadísticas agregadas por dispositivo
- `ranking_idle.csv`: ranking de modelos por rendimiento en cada resolución
  (en reposo)

**Resúmenes:**
- `viability_summary.txt`: resumen legible (rendimiento, degradación,
  combinaciones viables)

**Visual:**
- `input_frame_320x180.png`: frame de entrada de referencia
- `sample_outputs/`: ejemplos de salida de la superresolución

## Hallazgos principales

- **CPU_OCV (OpenCV):** tiempo real (≥30 fps) solo hasta 320×180. La mejor
  alternativa en CPU.
- **iGPU_OCL (iGPU Intel, OpenCL):** el sobrecoste de despacho deja una
  única resolución viable (128×72). Consistente bajo carga, pero peor que
  la CPU en casi todos los casos.
- **dGPU_OCL (RTX 5060, OpenCL):** varianza alta bajo carga y problemas de
  latencia de lanzamiento. Solo viable con entradas muy pequeñas pese al
  ancho de banda teórico.
- **dGPU_CUDA (RTX 5060, CUDA):** domina con 895-986 fps a 224×224
  (modelos ONNX).
- **iGPU_OV (iGPU Intel, OpenVINO):** 336 fps a 224×224 y rendimiento
  consistente bajo carga. La vía que se explota en las fases siguientes
  del trabajo.
- **CPU_OV (OpenVINO en CPU):** 88 fps a 224×224; competitiva para
  entradas pequeñas y portable.

## Organización de los ficheros

```
results/
├── README.md                 (este fichero)
├── RESULTS_SUMMARY.md        (tablas: combinaciones viables, degradación, rankings, fallos)
├── INTERPRETATION.md         (análisis técnico y recomendaciones)
├── DATA_DICT.md              (definición de columnas y abreviaturas)
├── VIABILITY_TABLE.md        (tabla completa de viabilidad)
├── viability_results.csv     (datos crudos)
├── full_stats.csv            (indicadores por combinación)
├── summary_by_device.csv     (estadísticas por dispositivo)
├── ranking_idle.csv          (ranking de modelos)
├── viability_summary.txt     (resumen)
├── input_frame_320x180.png   (frame de referencia)
└── sample_outputs/           (imágenes reescaladas)
```

## Reproducción

Desde `benchmarks/viability/`:

```bash
./run_viability_matrix.sh
```

Los resultados se escriben en `viability_results.csv` con las estadísticas
agregadas en `summary_by_device.csv`.
