# TFG — Superresolución en Pipeline de Juego

## Estructura del proyecto

```
TFG_CODE/
├── [CAPA 1 - Pipeline real]          # Intercepta frames del juego
│   ├── wrapper_swapbuffers_shm.c     ← LD_PRELOAD: captura frames
│   ├── build.sh                      ← compila el wrapper
│   ├── run_ai_pipeline.sh            ← lanza pipeline completo
│   ├── preparar_demo.sh              ← demo automática con juego
│   └── realtime_display_igpu.py      ← inferencia SR en tiempo real
│
├── [CAPA 2 - Benchmark con SHM]      # Mide el pipeline real
│   ├── benchmark_models.py           ← lee frames del SHM, mide latencia
│   └── benchmark_realesrgan_igpu.py  ← igual, específico RealESRGAN/iGPU
│
├── [CAPA 3 - Viabilidad]
│   └── viability/
│       ├── benchmark_standalone.py   ← núcleo: mide un modelo
│       ├── run_viability_matrix.sh   ← ejecuta todo (6 devs × N res × 4 cargas)
│       ├── run_quality_showcase.sh   ← genera imágenes + PSNR/SSIM
│       ├── analyze_viability_tfg.py  ← genera 32 gráficas + LaTeX + resumen
│       └── stressors/
│           ├── igpu_stress.py        ← satura iGPU
│           └── dgpu_stress.py        ← satura dGPU
│
├── [CAPA 4 - Fase 2]                 # Comparativa híbrida
│   └── phase2/
│       ├── generate_test_frames.py   ← genera imágenes de test
│       ├── metrics.py                ← PSNR / SSIM
│       └── compare_hybrid.py        ← compara estrategias
│
└── models/                           # Modelos pre-entrenados (.pb/.onnx/.xml)
    ├── FSRCNN_x2.pb
    ├── FSRCNN_x3.pb
    ├── FSRCNN_x4.pb
    ├── RealESRGAN_x4.onnx
    ├── super-resolution-10.onnx
    └── single-image-super-resolution-1032.xml/.bin
```

---

## Cómo funciona cada capa

### Capa 1 — Pipeline real (LD_PRELOAD)

```
juego → glSwapBuffers() → INTERCEPTADO por wrapper_swapbuffers_shm.c
             ↓
        glReadPixels() → copia frame a /dev/shm/game_frames (memoria compartida)
             ↓
        realtime_display_igpu.py lee el SHM → pasa al modelo SR → muestra resultado
```

El truco central es `LD_PRELOAD`: al lanzar el juego con la librería `.so` en `LD_PRELOAD`,
el sistema enlaza primero nuestro `wglSwapBuffers`/`glXSwapBuffers` en lugar del original.
Cada vez que el juego termina de renderizar un frame, nuestro wrapper lo captura con
`glReadPixels`, lo copia a memoria compartida POSIX (`/dev/shm/`) y escribe un número
de secuencia para que el consumidor sepa que hay un frame nuevo.

`realtime_display_igpu.py` corre en paralelo, lee continuamente el SHM y pasa cada
frame por el modelo de superresolución seleccionado.

**Para ejecutarlo:**
```bash
bash build.sh                            # compila wrapper → wrapper_swapbuffers_shm.so
bash run_ai_pipeline.sh                  # lanza pipeline: wrapper + juego + inferencia
bash preparar_demo.sh cpu idle <juego>   # demo automática completa
```

---

### Capa 3 — Viabilidad (resultados principales del TFG)

Estudia si cada dispositivo puede correr inferencia SR lo suficientemente rápido
para ser útil en un pipeline de juego, y cuánto se degrada bajo carga del sistema.

**Flujo de datos:**
```
imagen de entrada (real o sintética)
        ↓
benchmark_standalone.py
        ↓  warmup (5 iters, descartadas)
        ↓  medición (30 iters) → lista de latencias en ms
        ↓  PSNR / SSIM vs interpolación bicúbica
        ↓  (opcional) guarda imagen comparativa: input | bicubic | modelo
        ↓
viability_results.csv   (una fila por ejecución)
        ↓
analyze_viability_tfg.py
        ↓
32 gráficas PNG + latex_tables.tex + viability_summary.txt
```

**Dispositivos soportados:**

| ID | Backend | Modelos compatibles |
|----|---------|---------------------|
| `CPU_OCV` | OpenCV DNN, target CPU | `.pb` (FSRCNN) |
| `iGPU_OCL` | OpenCV DNN, target OpenCL Intel | `.pb` (FSRCNN) |
| `dGPU_OCL` | OpenCV DNN, target OpenCL NVIDIA | `.pb` (FSRCNN) |
| `CPU_OV` | OpenVINO, device CPU | `.onnx` / `.xml` |
| `iGPU_OV` | OpenVINO, device GPU (Intel) | `.onnx` / `.xml` |
| `dGPU_CUDA` | ONNX Runtime, CUDAExecutionProvider | `.onnx` |

**Estados de carga simulados:**

| Tag | Stressor |
|-----|---------|
| `idle` | Sin carga extra |
| `cpu` | `stress --cpu 16` (deja 4 cores libres) |
| `igpu` | `stressors/igpu_stress.py` (OpenVINO GPU en bucle) |
| `dgpu` | `stressors/dgpu_stress.py` (ONNX Runtime CUDA en bucle) |

---

## Funciones clave — `benchmark_standalone.py`

| Función | Qué hace |
|---------|---------|
| `load_input_image(path, w, h)` | Carga imagen real de disco y redimensiona |
| `make_test_frame(w, h, scene_type)` | Genera frame tipo-juego (gradiente / bordes / mixed) |
| `get_input_image(args, w, h)` | Decide entre imagen real o sintética según `--image` |
| `run_opencv_dnn(model, device, img, ...)` | Inferencia FSRCNN via OpenCV DNN |
| `run_openvino(model, device, img, ...)` | Inferencia RealESRGAN / SR-10 / SISR-1032 via OpenVINO |
| `run_onnxruntime_cuda(model, img, ...)` | Inferencia via CUDA (dGPU NVIDIA) |
| `quality_metrics(input_bgr, output_bgr)` | Devuelve (PSNR, SSIM) del modelo vs bicubic |
| `save_comparison(input, output, path)` | Guarda tira horizontal: input / bicubic / modelo |
| `percentile_stats(latencias)` | mean, std, p50, p90, p99, min, max |

**Nota sobre SISR-1032:** este modelo tiene dos entradas (LR + bicubic HR) y devuelve
un **residuo**, no la imagen directamente. La salida correcta es `bicubic_HR + residuo`.
Si se ignora esto el output es una imagen casi negra (PSNR ≈ 5 dB).

---

## Comandos para ejecutar

```bash
# 1. Experimentos de rendimiento (todas las resoluciones, 4 estados de carga)
bash viability/run_viability_matrix.sh

# Opciones útiles:
bash viability/run_viability_matrix.sh --smoke              # subset rápido (verificación)
bash viability/run_viability_matrix.sh --loads idle,cpu     # solo esos estados
bash viability/run_viability_matrix.sh --devices CPU_OV     # solo ese dispositivo
bash viability/run_viability_matrix.sh --iters 50           # más iteraciones

# 2. Imágenes comparativas + PSNR/SSIM (quality showcase)
bash viability/run_quality_showcase.sh

# Con imagen real:
bash viability/run_quality_showcase.sh --image /ruta/foto.jpg
# Con frame sintético específico:
bash viability/run_quality_showcase.sh --scene checkerboard

# 3. Análisis y generación de gráficas
python3 viability/analyze_viability_tfg.py

# Genera en viability/results/:
#   plots_tfg/         32 gráficas PNG
#   latex_tables.tex   tablas para TFG
#   viability_summary.txt
#   full_stats.csv
#   quality_results.csv (si se corrió el showcase)
```

---

## Ficheros imprescindibles

| Fichero | Para qué |
|---------|---------|
| `wrapper_swapbuffers_shm.c` | Pipeline real — compilar con `build.sh` |
| `build.sh` | Compila el wrapper LD_PRELOAD |
| `run_ai_pipeline.sh` | Orquesta el pipeline real |
| `preparar_demo.sh` | Demo automática completa |
| `viability/benchmark_standalone.py` | **Núcleo de toda la viabilidad** |
| `viability/run_viability_matrix.sh` | Ejecuta la matriz completa de experimentos |
| `viability/run_quality_showcase.sh` | Imágenes comparativas + calidad |
| `viability/analyze_viability_tfg.py` | Todas las gráficas y tablas para el TFG |
| `viability/stressors/igpu_stress.py` | Genera carga sostenida en iGPU |
| `viability/stressors/dgpu_stress.py` | Genera carga sostenida en dGPU |
| `phase2/generate_test_frames.py` | Genera frames sintéticos tipo-juego |
| `models/*.pb / *.onnx / *.xml` | Modelos pre-entrenados de SR |

**Ficheros prescindibles (exploraciones anteriores, suplantados):**

| Fichero | Suplantado por |
|---------|---------------|
| `benchmark_models.py` | `viability/benchmark_standalone.py` |
| `benchmark_realesrgan_igpu.py` | `viability/benchmark_standalone.py` |
| `viability/benchmark_frame_injection.py` | `run_viability_matrix.sh` |
| `viability/analyze_viability.py` | `analyze_viability_tfg.py` |
| `phase2/compare_hybrid.py` | (fase 2, aún no activa) |

---

## Resultados principales

### Rendimiento idle a ~320×180

| Dispositivo | Modelo | FPS (p50) | Latencia p50 |
|------------|--------|-----------|-------------|
| dGPU CUDA | RealESRGAN ×4 | **986** | 1.01 ms |
| dGPU CUDA | SR-10 | **895** | 1.12 ms |
| iGPU OV | SR-10 | 336 | 2.98 ms |
| iGPU OV | RealESRGAN ×4 | 335 | 2.99 ms |
| CPU OV | RealESRGAN ×4 | 89 | 11.3 ms |
| CPU OCV | FSRCNN ×2 | 56 | 17.9 ms |
| iGPU OCL | FSRCNN ×2 | 21 | 48.4 ms |
| dGPU OCL | FSRCNN ×2 | 26 | 39.1 ms |

### Degradación bajo carga del sistema

| Dispositivo | Carga CPU | Carga iGPU | Carga dGPU |
|------------|-----------|-----------|-----------|
| CPU (OCV) | +10.6% | -0.4% | +8.0% |
| CPU (OV) | **+49.9%** | +2.3% | +9.0% |
| iGPU (OCL) | -4.4% | -1.5% | +9.3% |
| iGPU (OV) | +7.5% | +1.1% | +13.8% |
| dGPU (OCL) | +2.5% | +0.6% | +23.9% |
| dGPU (CUDA) | -8.2% | -4.2% | **+64.2%** |

### Calidad (PSNR vs bicubic, frame tipo-juego)

| Modelo | PSNR medio | SSIM medio |
|--------|-----------|-----------|
| SISR-1032 (residual) | **45.0 dB** | 0.9947 |
| FSRCNN ×2 | 43.0 dB | 0.9898 |
| FSRCNN ×4 | 40.4 dB | 0.9854 |
| FSRCNN ×3 | 40.3 dB | 0.9858 |
| RealESRGAN ×4 | 31.9 dB | 0.9395 |
| SR-10 | 31.9 dB | 0.9395 |

---

## Conclusión de viabilidad

**Mejor candidato para pipeline paralelo al juego:** `iGPU_OV` (OpenVINO sobre Intel iGPU).
- 335 FPS con RealESRGAN/SR-10 a 224×224
- Solo +13.8% de degradación cuando la dGPU está ocupada renderizando el juego
- Deja la dGPU completamente libre para el juego

**Por qué no dGPU CUDA:** es el más rápido en idle (986 FPS) pero compite directamente
con el renderizado del juego (+64% degradación). No es viable para pipeline simultáneo.

**Por qué no CPU OV:** degrada +50% bajo carga CPU (el juego también usa CPU).
