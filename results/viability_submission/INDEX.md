# Paquete de resultados del estudio de viabilidad

Benchmark completo de viabilidad para upscaling con IA en tiempo real.
Contenido del paquete:

## Gráficas (`plots/`)

1. **device_ranking_idle.png**: ranking de FPS por dispositivo (sin carga).
   Muestra la jerarquía dGPU_OCL > iGPU > CPU.
2. **latency_vs_resolution.png**: latencia frente a resolución de entrada
   (4 estados de carga). Muestra el escalado de cada dispositivo y su
   degradación bajo carga.
3. **fps_comparison.png**: FPS por modelo (comparativa agrupada). Diferencias
   entre FSRCNN_x2/x3/x4 y el modelo de OpenVINO.
4. **interference_heatmap.png**: impacto de los generadores de carga
   (dispositivos × carga). Muestra qué dispositivos son inmunes al estrés
   de CPU.
5. **model_quality_proxy.png**: dispersión latencia frente a factor de
   escala. Muestra el compromiso calidad/velocidad.

## Comparativas visuales (`comparisons/`)

14 imágenes representativas:

- **CPU_OCV** (2): referencia lenta, con y sin estrés de CPU
- **CPU_OV** (2): OpenVINO en CPU, mejora respecto a OpenCV
- **iGPU_OCL** (2): GPU integrada, 2 resoluciones
- **iGPU_OV** (2): GPU integrada con OpenVINO, para comparar con OpenCL
- **dGPU_OCL** (6): 3 resoluciones (320×180, 640×360, 1280×720) sin carga,
  más 2 pruebas de interferencia (estrés de CPU y de memoria) a 640×360.
  Mejor rendimiento global.

Cada PNG muestra: original | bicúbico | upscaling IA (con PSNR y FPS).

## Documentación (`docs/`)

1. **RESULTS_SUMMARY.md**: combinaciones viables (≥30 FPS), ranking por
   dispositivo y modelo, degradación bajo carga.
2. **DATA_DICT.md**: definición de las columnas del CSV, umbrales de
   viabilidad y metodología de medición.
3. **INTERPRETATION.md**: por qué se comporta así cada dispositivo,
   limitaciones (formato ONNX, OpenCL frente a CUDA, etc.) y
   recomendaciones para la fase 2.

## Datos crudos (`data/`)

- **frame_injection_results.csv** (99 filas): latencias, FPS y PSNR de cada
  combinación dispositivo/modelo/resolución/interferencia.
- **summary_by_device.csv**: agregación por dispositivo.

---

**Hardware:** RTX 5060 (dGPU), Intel iGPU, CPU Intel Core
**Modelos:** FSRCNN_x2/x3/x4, RealESRGAN, single-image-super-resolution-1032 (OpenVINO)
**Resoluciones:** 320×180, 640×360, 1280×720
**Cargas:** sin carga, CPU (stress --cpu 8), memoria (reserva de 2 GB)
**Total de mediciones:** 99 combinaciones válidas (7,9 % de fallos por reshape en OpenVINO)
