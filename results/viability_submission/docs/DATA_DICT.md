# Diccionario de datos

## Definición de las columnas de los CSV

### viability_results.csv

| Columna | Tipo | Descripción | Unidades | Ejemplo |
|---------|------|-------------|----------|---------|
| `run_id` | string | Identificador único de la sesión de benchmark (por timestamp) | - | `run_20260423T175951` |
| `timestamp` | ISO-8601 | Momento exacto de la medición | - | `2026-04-23T17:59:51` |
| `device` | string | Dispositivo de ejecución (ver IDs más abajo) | - | `CPU_OCV`, `dGPU_CUDA` |
| `model` | string | Fichero del modelo (según framework) | - | `FSRCNN_x2.pb`, `super-resolution-10.onnx` |
| `input_w` | entero | Ancho del frame de entrada | píxeles | 320 |
| `input_h` | entero | Alto del frame de entrada | píxeles | 180 |
| `output_w` | entero | Ancho del frame de salida (tras el upscaling) | píxeles | 1280 |
| `output_h` | entero | Alto del frame de salida | píxeles | 720 |
| `load_tag` | string | Condición de carga del sistema (ver estados de carga) | - | `idle`, `cpu`, `igpu`, `dgpu` |
| `warmup` | entero | Iteraciones de inferencia previas al cronometraje (descartadas) | unidades | 5 |
| `iters` | entero | Iteraciones de inferencia cronometradas | unidades | 30 |
| `wall_s` | float | Tiempo total de reloj (todas las iteraciones más overhead) | segundos | 3.303 |
| `mean_ms` | float | Latencia media de todas las iteraciones | ms | 48.429 |
| `std_ms` | float | Desviación estándar de la latencia | ms | 0.693 |
| `p50_ms` | float | Latencia mediana (percentil 50) | ms | 48.375 |
| `p90_ms` | float | Latencia en el percentil 90 (garantía para el 90 % de los frames) | ms | 49.209 |
| `p99_ms` | float | Latencia en el percentil 99 | ms | 49.844 |
| `min_ms` | float | Latencia mínima observada | ms | 47.113 |
| `max_ms` | float | Latencia máxima observada | ms | 50.008 |
| `fps_mean` | float | Rendimiento según la latencia media (1000/mean_ms) | fps | 20.65 |
| `fps_p50` | float | Rendimiento según la latencia mediana (1000/p50_ms) | fps | 20.67 |
| `active_backend_name` | string | Backend o fabricante reportado por el dispositivo | - | `Intel(R) Graphics`, `CUDA:RTX5060` |

### full_stats.csv

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `device` | string | ID del dispositivo |
| `model` | string | Fichero del modelo |
| `input_w` | entero | Ancho de entrada |
| `input_h` | entero | Alto de entrada |
| `load_tag` | string | Condición de carga |
| `p50_ms` | float | Latencia mediana |
| `p90_ms` | float | Percentil 90 |
| `p99_ms` | float | Percentil 99 |
| `mean_ms` | float | Latencia media |
| `fps_p50` | float | Rendimiento en p50 |
| `degradation_pct` | float | Pérdida de rendimiento bajo carga respecto a idle |
| `viable_30fps` | string | SI / NO: alcanza ≥30 fps (p50 < 33,3 ms) |
| `viable_60fps` | string | SI / NO: alcanza ≥60 fps (p50 < 16,7 ms) |

### summary_by_device.csv

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `device` | string | ID del dispositivo |
| `load` | string | Condición de carga |
| `n_cells` | entero | Número de combinaciones modelo-resolución probadas |
| `mean_of_mean` | float | Media de las latencias medias de todas las celdas |
| `mean_of_p50` | float | Media de las latencias p50 |
| `mean_of_p90` | float | Media de las latencias p90 |
| `mean_of_fps_p50` | float | Media de fps_p50 |

### ranking_idle.csv

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `model` | string | Fichero del modelo |
| `input_w` | entero | Ancho de entrada |
| `input_h` | entero | Alto de entrada |
| `rank` | entero | 1 = más rápido, 2 = segundo, 3 = más lento |
| `device` | string | Dispositivo en esa posición |
| `p50_ms` | float | Latencia mediana en esa posición |
| `fps_p50` | float | Rendimiento en esa posición |

---

## IDs de dispositivo y abreviaturas

| ID | Nombre completo | Backend | Hardware | Notas |
|----|-----------------|---------|----------|-------|
| `CPU_OCV` | CPU OpenCV | OpenCV DNN | Intel Core Ultra 7 265K | Implementación de respaldo en CPU, se paraleliza sola |
| `iGPU_OCL` | iGPU OpenCL | OpenCL | Intel Graphics (iGPU) | GPU integrada del Core Ultra 7 265K |
| `dGPU_OCL` | dGPU OpenCL | OpenCL | NVIDIA RTX 5060 | GPU dedicada vía OpenCL 1.2 |
| `dGPU_CUDA` | dGPU CUDA | CUDA 12.x | NVIDIA RTX 5060 | GPU dedicada vía CUDA (solo modelos ONNX) |
| `CPU_OV` | CPU OpenVINO | OpenVINO (CPU) | Intel Core Ultra 7 265K | Modelos ONNX vía runtime de OpenVINO |
| `iGPU_OV` | iGPU OpenVINO | OpenVINO (GPU) | Intel Graphics (iGPU) | Modelos ONNX vía plugin GPU de OpenVINO |

---

## Estados de carga

| Etiqueta | Descripción | Cómo se genera | Propósito |
|----------|-------------|----------------|-----------|
| `idle` | Sistema en reposo (sin cargas que compitan) | El benchmark corre solo | Medida de referencia |
| `cpu` | Contención de CPU | 12 hilos al 100 % con carga sintética | Robustez frente a colas de CPU en el host |
| `igpu` | Contención de iGPU | Kernel OpenCL propio en rejilla 8×32 en paralelo | Compartición de la iGPU y conflictos de memoria |
| `dgpu` | Contención de dGPU | Kernel CUDA u OpenCL en rejilla 32×32 | Cambios de contexto en la GPU dedicada |

Cada condición de carga sustituye a la anterior; se mide en ejecuciones
separadas, no concurrentes.

---

## Modelos

| Modelo | Tipo | Framework | Entrada | Salida | Notas |
|--------|------|-----------|---------|--------|-------|
| `FSRCNN_x2.pb` | Superresolución | TensorFlow/Protobuf | cualquier W×H | 2W × 2H | CNN ligera, escala 2× |
| `FSRCNN_x3.pb` | Superresolución | TensorFlow/Protobuf | cualquier W×H | 3W × 3H | CNN ligera, escala 3× |
| `FSRCNN_x4.pb` | Superresolución | TensorFlow/Protobuf | cualquier W×H | 4W × 4H | CNN ligera, escala 4× |
| `RealESRGAN_x4.onnx` | Superresolución | ONNX | 224×224 (fija) | 896×896 | Modelo grande, escala 4× |
| `super-resolution-10.onnx` | Superresolución | ONNX | 224×224 (fija) | 672×672 | Escala 3×, ligero |
| `single-image-super-resolution-1032.xml` | Superresolución | OpenVINO IR | 480×270 | 1920×1080 | Formato IR de OpenVINO |

**Nota:** los modelos .pb (Protobuf) y .xml (OpenVINO IR) admiten entradas de
tamaño variable. Los .onnx requieren 224×224 (reshape fijado en el código de
inferencia). Todos los modelos trabajan con RGB o escala de grises, con
entrada de un solo frame.

---

## Umbrales de viabilidad

| Umbral | Definición | Justificación |
|--------|-----------|---------------|
| ≥30 fps | `p50_ms < 33,3 ms` | Tasa mínima habitual en videojuegos |
| ≥60 fps | `p50_ms < 16,7 ms` | Tasa de refresco estándar de los monitores (1000/60 ≈ 16,67) |
| Tiempo real | ≥30 fps sin carga | Aceptable para aplicaciones interactivas |

**Nota:** las medidas usan la **mediana (p50)** y no la media, porque la
distribución de latencias no es normal (cola a la derecha). p50 es la
garantía para el 50 % de los frames; p90, el peor caso para el 90 %.

---

## Métricas derivadas

| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| `fps_p50` | 1000 / p50_ms | Rendimiento si cada frame tardase exactamente p50 |
| `degradation_pct` | 100 × (latencia_carga - latencia_idle) / latencia_idle | Ralentización porcentual por la carga que compite |
| `viable_30fps` | p50_ms ≤ 33,3 ms | ¿Alcanza 30 fps? |
| `viable_60fps` | p50_ms ≤ 16,7 ms | ¿Alcanza 60 fps? |
| `p90/p50` | p90_ms / p50_ms | Indicador de estabilidad (menor = más consistente) |

---

## Unidades y precisión

- **Latencia:** milisegundos (ms), precisión ±0,01 ms
- **FPS:** frames por segundo, calculados como 1000 / latencia_ms
- **Degradación:** porcentaje (%), cambio relativo
- **Timestamps:** ISO-8601 UTC
- **Resolución:** píxeles (ancho × alto)
