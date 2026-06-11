# Fase 1 Viabilidad + FSRCNN IR

## Notas importantes

---

### P1: ¿Como se lanzaron los experimentos?

**Respuesta:**
Script bash `run_viability_matrix.sh` que:
1. Define matriz: 6 dispositivos × 6 modelos × N resoluciones × 4 estados carga
2. Arranca/para stressors (CPU stress, iGPU stress, dGPU stress) entre estados
3. Ejecuta `benchmark_standalone.py` para cada combo
4. Recoge CSV con FPS, latencia (p50/p90/p99), PSNR

Flujo:
```
benchmark_standalone.py \
  --model models/FSRCNN_x2.pb \
  --device CPU_OCV \
  --input_size 320 180 \
  --warmup 5 --iters 30 \
  --load_tag idle \
  --out_csv viability/results/viability_results.csv
```

Total: 580 filas CSV. ~2-3 horas ejecución.

---

### P2: ¿Cuales son los 6 dispositivos?

**Respuesta:**

| Device | Hardware | Backend | Formato |
|--------|----------|---------|---------|
| CPU_OCV | Intel CPU | OpenCV DNN | .pb (TensorFlow) |
| CPU_OV | Intel CPU | OpenVINO | .onnx / .xml |
| iGPU_OCL | Intel Iris (integrada) | OpenCV + OpenCL | .pb |
| iGPU_OV | Intel Iris | OpenVINO GPU | .onnx / .xml |
| dGPU_OCL | RTX 5060 | OpenCV + OpenCL | .pb |
| dGPU_CUDA | RTX 5060 | ONNX Runtime | .onnx |

Hardware: 1 CPU + 1 iGPU + 1 dGPU = 3 físicos.
Pero 6 combos device/backend/formato distintos.

**Hallazgo clave:** dGPU_OCL (25 FPS) vs dGPU_CUDA (986 FPS) = mismo hardware, backend diferente = 40× diferencia. OpenCL no es competitive en NVIDIA.

---

### P3: ¿Cómo se verificó que iGPU_OCL y dGPU_OCL eran dispositivos reales y no intercambiados?

**Respuesta:**

Cada corrida escribe `active_backend_name` en CSV:
```python
d = cv2.ocl.Device_getDefault()
active_device_name = d.name() if d else "CPU"
```

CSV muestra:
```
iGPU_OCL → active_backend_name = "Intel(R) Graphics"
dGPU_OCL → active_backend_name = "NVIDIA GeForce RTX 5060"
```

Variable de entorno fuerza dispositivo:
```bash
OPENCV_OPENCL_DEVICE=Intel:GPU:0   # iGPU_OCL
OPENCV_OPENCL_DEVICE=NVIDIA:GPU:0  # dGPU_OCL
```

Verificado 176 filas iGPU_OCL, 148 filas dGPU_OCL — mismo hardware, distinto nombre.

---

### P4: ¿PSNR 37 dB con imagen de juego es "bueno"? ¿Vs qué lo comparas?

**Respuesta:**

PSNR vs bicúbico (baseline industrial):
- FSRCNN ×2: 38.5 dB → 10 dB superior a bicúbico
- RealESRGAN: 28.1 dB → inferior a FSRCNN
- Bicúbico: 0 dB (por definición)

Métrica relativa, no absoluta. "38.5 dB mejor que bicúbico" en textura Minecraft significa:
- Líneas rectas más nítidas
- Menos blur respecto a bicúbico
- Imperceptible visualmente pero medible

Imagen real mine.png: PSNR consistente independiente del dispositivo (mismo modelo = mismo resultado).

---

### P5: ¿Por qué concertimos FSRCNN a OpenVINO? ¿Qué cambió?

**Respuesta:**

**Problema inicial:**
- FSRCNN .pb (OpenCV DNN): 19 FPS @ 320×180 (marginal)
- ONNX (OpenVINO): 335 FPS @ 224×224 pero entrada **FIJA**

Idea: convertir .pb → IR (OpenVINO Intermediate Representation).

**Conversión:**
```bash
ovc models/FSRCNN_x2.pb --output_model models/openvino_ir/FSRCNN_x2
# Genera: FSRCNN_x2.xml + FSRCNN_x2.bin
```

**Qué pasó:**
- Mismo modelo, mismos pesos, misma calidad (PSNR 38.5 dB idéntico)
- OpenVINO recompila con kernels optimizados Intel (AVX/VNNI en CPU, oneAPI en GPU)
- **Velocidad:** 19 FPS → 496 FPS (CPU), 270 FPS (iGPU)

OpenCV DNN ejecuta grafo genérico. OpenVINO ejecuta grafo compilado con SIMD directo.

---

### P6: Código necesario para ejecutar el experimento final (iGPU IR)

**Respuesta:**

**Paso 1: Convertir modelo**
```bash
ovc models/FSRCNN_x2.pb --output_model models/openvino_ir/FSRCNN_x2
```

**Paso 2: Benchmark simple**
```bash
python3 viability/benchmark_standalone.py \
  --model models/openvino_ir/FSRCNN_x2.xml \
  --device iGPU_OV \
  --input_size 320 180 \
  --warmup 5 --iters 30 \
  --load_tag idle \
  --image mine.png \
  --save_outputs \
  --out_csv results.csv
```

**Salida esperada:**
```
[OK] iGPU_OV FSRCNN_x2.xml 320x180 idle
  mean=3.57ms p50=3.28ms p90=4.03ms p99=4.40ms
  FPS(p50)=305.1 PSNR=28.80 SSIM=0.9662
```

**Paso 3: Matriz completa (todos los combos)**
```bash
bash viability/run_fsrcnn_ir_matrix.sh
# Ejecuta 208 combos: CPU_OV/iGPU_OV × 3 modelos × 7-10 resoluciones × 4 loads
# ~20 min, genera viability_results_fsrcnn_ir.csv
```

---

### P7: Arquitectura del benchmark — ¿cómo se mide la latencia pura?

**Respuesta:**

**Flujo:**
1. Carga imagen real (mine.png)
2. Redimensiona a input_size solicitado (INTER_LANCZOS4)
3. **Warmup:** 5 iteraciones descartadas (descarta overhead de load de modelo)
4. **Medición:** 30 iteraciones con `time.perf_counter()` antes/después inferencia
5. Calcula: p50, p90, p99, mean, std
6. Calcula PSNR comparando salida vs bicúbico

**Pseudocódigo:**
```python
sr = DnnSuperResImpl_create()
sr.readModel(model_path)
sr.setModel(kind, scale)
sr.setPreferableTarget(target)  # CPU, OpenCL, CUDA

# Warmup (descartado)
for _ in range(5):
    sr.upsample(img)

# Medición
latencies = []
for _ in range(30):
    t0 = perf_counter()
    output = sr.upsample(img)
    latencies.append((perf_counter() - t0) * 1000)  # ms

fps = 1000 / percentile(latencies, 50)
```

**Por qué es "puro":**
- No incluye overhead de captura (frames del juego)
- No incluye overhead de display
- Solo la inferencia del modelo
- Multiplicable por arquitectura real después (fase 2)

---

### P8: ¿Cuál es el siguiente paso (fase 2)?

**Respuesta:**

**Hipótesis fase 2:**
Renderizar a baja resolución (ej. 320×180) + upscalear con FSRCNN IR en iGPU es más rápido que renderizar nativo (640×360) si:
```
tiempo(render_320 + upscale_iGPU_320→640) < tiempo(render_640_nativo)
```

**Experimento:**
1. Hook en motor (LD_PRELOAD wrapper o integración nativa)
2. Captura frames del juego a 320×180
3. Upscalea en iGPU en paralelo → 640×360
4. Mide FPS total, GPU load, calidad visual
5. Compara vs renderizado nativo a 640×360

**Métricas:**
- FPS total (frames por segundo)
- GPU load (utilización %)
- Latencia frame-a-frame
- PSNR vs nativo (calidad)

---

## Datos clave a llevar impresos

### Tabla 1: Resumen viabilidad (580 mediciones)
```
Dispositivo        Modelo          Entrada   FPS    Viable?
─────────────────────────────────────────────────────────
dGPU CUDA         RealESRGAN      224×224   986    ✓ Sí
iGPU OpenVINO     RealESRGAN      224×224   335    ✓ Sí
CPU OpenVINO      RealESRGAN      224×224    88    ✓ Sí (degrada)
CPU OpenCV DNN    FSRCNN_x4       320×180    19    ~ Marginal
dGPU OpenCL       FSRCNN_x2       320×180    25    ✗ No
iGPU OpenCL       FSRCNN_x2       320×180    20    ✗ No
```

### Tabla 2: Conversión FSRCNN a IR (208 mediciones)
```
Modelo      Backend         Entrada   Salida      FPS OpenCV  FPS IR    Ganancia
───────────────────────────────────────────────────────────────────────────
FSRCNN_x2   CPU_OV          320×180   640×360     67          588       8.8×
FSRCNN_x2   iGPU_OV         320×180   640×360     67          304       4.5×
FSRCNN_x4   iGPU_OV         480×270   1920×1080   6           117       19×
FSRCNN_x4   iGPU_OV         640×360   2560×1440   2           58        29×
```

### Tabla 3: Calidad (PSNR vs bicúbico, imagen real)
```
Modelo                  PSNR (mine.png)  Escala
────────────────────────────────────────────────
FSRCNN ×2 IR            38.5 dB          ×2
FSRCNN ×3 IR            35.7 dB          ×3
FSRCNN ×4 IR            34.8 dB          ×4
RealESRGAN ×4           28.1 dB          ×3 (224×224 fijo)
Bicúbico baseline        0.0 dB          (referencia)
```

---

## Respuestas cortas para preguntas técnicas rápidas

**P: ¿Cuánto tarda cada experimento?**
A: 5-30 ms por modelo, ~30 iteraciones. Con 580 combos y stressors = 2-3 horas total.

**P: ¿Qué es `load_tag`?**
A: Estado del sistema: idle (sin carga), cpu (stress --cpu 16), igpu (saturar iGPU), dgpu (saturar dGPU).

**P: ¿OpenVINO vs TensorRT vs TorchScript?**
A: OpenVINO: open-source, Intel-nativo, funciona en CPU/GPU. TensorRT: NVIDIA-only, más rápido en RTX. Elegí OpenVINO porque iGPU + CPU en mismo framework.

**P: ¿Resolución 224×224 para ONNX es suficiente para un juego?**
A: No. Es un cuello de botella. Por eso FSRCNN IR es ganador: entrada flexible (320×180 a 1920×1080), velocidad equivalente a ONNX.

**P: ¿PSNR 38 dB es mejor que OpenGL upscaling?**
A: No comparable: OpenGL es hardware built-in, FSRCNN es AI. PSNR mide diferencia vs bicúbico, no vs realidad. Mejor métrica: SSIM + test visual.

---

## Estructura física de carpetas para mostrar

```
viability/
├── benchmark_standalone.py       ← Script único que todo ejecuta
├── run_viability_matrix.sh       ← Orquesta 580 combos
├── run_fsrcnn_ir_matrix.sh       ← Orquesta 208 combos IR
├── results/
│   ├── viability_results.csv                 ← 580 filas, FPS/latencia
│   ├── viability_results_fsrcnn_ir.csv       ← 208 filas, FPS/latencia IR
│   ├── quality_game.csv                      ← PSNR con mine.png
│   ├── plots/                                ← Gráficas finales
│   ├── comparisons_game_full/                ← 113 imágenes (Original|Bicubic|AI)
│   └── comparisons_ir/                       ← 12 imágenes IR
├── models/openvino_ir/
│   ├── FSRCNN_x2.xml + .bin
│   ├── FSRCNN_x3.xml + .bin
│   └── FSRCNN_x4.xml + .bin
└── stressors/
    ├── igpu_stress.py
    └── dgpu_stress.py
```

---

## Preguntas que TÚ deberías hacer al tutor

1. **¿Fase 2 requiere integración con motor gráfico real o vale simulación?**
   - Real = más trabajo, más realista
   - Simulación = más rápido, menos incertidumbre

2. **¿FSRCNN IR es el candidato ganador o quieres comparar más opciones?**
   - RealESRGAN tiene mejor reputación pero PSNR es peor aquí

3. **¿Timing para reuniones futuras / presentación final?**
   - Cuándo necesita tener fase 2 lista

4. **¿Qué métrica importa más: FPS, calidad (PSNR), o GPU load?**
   - Trade-off diferente según objetivo final

