# Plan de experimentos — Arquitectura híbrida vs dedicada

Objetivo global: **demostrar con datos que existe un régimen donde hacer el
upscaling en la iGPU (híbrida) es mejor que hacerlo en la dGPU (dedicada)**,
porque la dGPU ya está saturada renderizando el juego.

---

## 0. La afirmación a demostrar (y la honestidad por delante)

Hay DOS formas de que la híbrida "gane", y conviene distinguirlas:

- **(A) Versión fuerte — cruce de inferencia bruta:** cuando la dGPU está
  saturada, su tiempo de inferencia se vuelve PEOR que el de la iGPU.
  → Riesgo: la dGPU (RTX 5060) es muy potente; puede que ni saturada baje de
  la iGPU. En la viabilidad, la dGPU saturada (sintético) seguía por encima.

- **(B) Versión robusta — la IA en la dGPU roba FPS al juego:** poner la IA en
  la dGPU compite con el render → bajan los FPS del juego. Ponerla en la iGPU
  (libre) no los toca. → Esto es casi seguro cierto y es la demostración sólida.

**Estrategia: perseguir (A) pero apoyarse en (B).** Si (A) no se da, (B) ya
justifica la arquitectura. Reportar lo que digan los datos, sin forzar.

---

## 1. Prerrequisitos (FASE 0 — hay que resolver antes)

1. **Inferencia en la dGPU (CRÍTICO, ahora falta):** el venv solo tiene
   `CPUExecutionProvider`. Para medir IA en la dGPU hace falta una vía CUDA:
   - Opción 1: `onnxruntime-gpu` con CUDA compatible. OJO: RTX 5060 es Blackwell
     (muy nueva) → requiere CUDA reciente; puede dar guerra de versiones.
   - Opción 2: PyTorch + CUDA (torch está en versión CPU).
   - Opción 3 (mala): OpenCV DNN OpenCL en NVIDIA (≈11 FPS, backend roto).
   → Verificar/instalar y confirmar con un test antes de nada.
2. **FSRCNN como ONNX:** para correr FSRCNN en la dGPU (CUDA) hace falta el
   modelo en ONNX (ahora está en .pb / IR). Convertir.
3. **Shaders en Minecraft:** Iris + Sodium + shader pack pesado (SEUS PTGI /
   Complementary a tope). Tarea del usuario. Versión 1.20.1 (PRIME ok).
4. **Escena reproducible:** un mundo fijo + posición fija (o un punto de
   guardado), para que todas las medidas comparen la MISMA escena. Sin esto las
   comparativas de FPS no son válidas.

---

## 2. Variables del estudio

| Eje | Valores |
|---|---|
| Modelos | FSRCNN x2/x3/x4, super-resolution-10, RealESRGAN x4 |
| Dispositivos | iGPU (OpenVINO), dGPU (CUDA/ORT), CPU (OpenVINO) |
| Resoluciones entrada | 128×72, 256×144, 320×180, 480×270, 640×360, 960×540, 1280×720, 1920×1080 |
| Factores de escala | x2, x3, x4 |
| Carga dGPU | idle, 25%, 50%, 75%, 100% (sintético) + real (shaders) |
| Repeticiones | warmup 5 + 50 iters por celda (p50/p95) |

---

## 3. Los experimentos

### Exp A — Barrido de inferencia (sin carga): dGPU vs iGPU vs CPU
**Qué:** matriz modelo × dispositivo × resolución × escala. Latencia y FPS de
inferencia pura.
**Para:** mapa base de qué dispositivo gana en cada combinación SIN carga.
**Salida:** una gráfica por (modelo, escala): FPS vs resolución de entrada, una
curva por dispositivo. + CSV.

### Exp B — Cruce bajo carga (la versión fuerte)
**Qué:** para cada nivel de carga de la dGPU (sintético 0→100% y luego real con
shaders), medir el tiempo de inferencia en la dGPU (cargada) y en la iGPU
(libre), con el modelo elegido y varias resoluciones.
**Para:** localizar el punto donde la iGPU iguala/supera a la dGPU.
**Salida:** gráfica latencia-inferencia vs carga-dGPU, curvas dGPU e iGPU;
marcar el cruce si existe. + CSV.

### Exp C — FPS de sistema completo: nativa vs híbrida vs dedicada (LA CLAVE)
**Qué:** con shaders pesados y escena fija, medir los FPS en tres configs:
1. **Nativa**: juego a 1080p, dGPU solo renderiza. (baseline de FPS)
2. **Dedicada (IA en dGPU)**: juego a 1080p + upscaling en la dGPU. (la IA
   compite con el render → FPS bajan)
3. **Híbrida (IA en iGPU)**: juego a baja resolución (la dGPU renderiza pocos
   píxeles → más FPS) + upscaling en la iGPU → salida 1080p.
**Para:** demostrar que la híbrida da más FPS jugables a la misma resolución de
salida. Es la demostración robusta (B).
**Salida:** tabla/gráfica de barras FPS por config y por resolución de render.
FPS de render se miden con `benchmarks/render_fps.py` (contador del buzón).

### Exp D — Calidad por combinación
**Qué:** PSNR/SSIM vs frame nativo real (ground truth) por (modelo, escala,
resolución). Extiende `phase2/quality_matrix.py`.
**Para:** el compromiso calidad-rendimiento, y completar el análisis.
**Salida:** tabla + gráfica calidad vs resolución por escala.

---

## 4. Automatización — qué construir (en `experiments/`)

| Script | Función |
|---|---|
| `setup_dgpu.sh` | Instala/verifica la vía CUDA de inferencia (Fase 0.1). |
| `convert_fsrcnn_onnx.py` | FSRCNN .pb/IR → ONNX (Fase 0.2). |
| `bench_inference.py` | Núcleo: mide 1 celda (modelo, dispositivo, res, escala, carga) → fila CSV. Reutiliza/extiende `benchmarks/viability/benchmark_standalone.py`. |
| `dgpu_load.py` | Carga de dGPU controlable por `--intensity` (0–100), para Exp B. |
| `run_expA.sh` | Orquesta el barrido completo de inferencia. |
| `run_expB.sh` | Orquesta el barrido de carga + medición de cruce. |
| `run_expC.sh` | Orquesta las 3 configs de sistema completo (necesita el juego). |
| `make_plots.py` | Genera TODAS las gráficas desde los CSVs (matplotlib). |
| `run_all.sh` | Orquestador maestro: A → B → D automáticos; C semiautomático. |

Reutilizamos lo que ya hay: `benchmark_standalone.py`, los stressors,
`render_fps.py`, `measure_latency.py`, `quality_matrix.py`.

---

## 5. Salidas esperadas (material para la memoria)

- **CSVs** por experimento en `results/experiments/`.
- **Gráficas** (PNG/PDF):
  - FPS vs resolución, una figura por (modelo × escala) — Exp A.
  - Latencia-inferencia vs carga-dGPU con el cruce — Exp B.
  - Barras FPS nativa/dedicada/híbrida — Exp C.
  - Calidad (PSNR/SSIM) vs resolución por escala — Exp D.
- **Tablas resumen** en Markdown listas para citar.

---

## 6. Riesgos y mitigación

- **El cruce (A) puede no darse**: la dGPU es muy potente. → La demostración
  recae en Exp C (B): la IA-en-dGPU roba FPS al juego, la IA-en-iGPU no.
- **CUDA + Blackwell (RTX 5060)**: posibles líos de versiones con onnxruntime-gpu.
  → Plan B: PyTorch-CUDA. Plan C: limitar el eje dGPU a OpenCL (peor pero
  disponible) y centrar la tesis en Exp C.
- **Escena no reproducible**: invalida las comparativas. → Mundo plano fijo +
  posición fija + misma hora del día en el juego.
- **Overhead de captura en la medida nativa**: medir también sin el wrapper
  para aislarlo.

---

## 7. Orden de ejecución

1. **Fase 0** — prereqs: vía CUDA + FSRCNN ONNX + shaders + escena fija.
2. **Exp A** — automático, sin juego. (horas)
3. **Exp B** — automático con carga sintética; repetir con shaders reales.
4. **Exp C** — con el juego + shaders + escena fija (la demostración clave).
5. **Exp D** — calidad, automático.
6. **Gráficas** (`make_plots.py`) + **documentar la memoria** con los datos.

---

## 8. Decisiones que necesito de ti antes de construir

1. ¿Resolvemos la vía CUDA (onnxruntime-gpu / torch-cuda) para medir la dGPU, o
   de momento centramos en iGPU vs CPU + Exp C (que es la demostración fuerte)?
2. ¿Qué modelos entran en la matriz? (todos, o FSRCNN + 1 ONNX para acotar)
3. ¿Tienes ya una escena fija de Minecraft pensada, o la definimos?
