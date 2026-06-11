# Game External Processing Pipeline (TFG)

Pipeline de captura de frames GPU en tiempo real con mejora por IA:
intercepta los frames OpenGL de un juego/aplicación (render en **dGPU
NVIDIA**), los transfiere por memoria compartida con latencia mínima, y
aplica superresolución en la **iGPU Intel** (OpenVINO), dejando la dGPU
libre para el render.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Juego/App     │    │ Memoria          │    │ Superresolución │
│  (dGPU NVIDIA)  │───▶│ compartida       │───▶│  (iGPU Intel)   │
│  LD_PRELOAD     │    │ /dev/shm (~0,1ms)│    │  10–15 ms       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| [`capture/`](capture/) | Interceptor C (`LD_PRELOAD` sobre `glXSwapBuffers`) → shm con header. Soporta glxgears y Minecraft (LWJGL3/GLFW). |
| [`processing/`](processing/) | Superresolución en iGPU: FSRCNN/OpenVINO (jugable, 75 FPS), sisr-1032 (calidad), ONNX, Real-ESRGAN; overlay ventana única; streaming Flask. |
| [`pipeline/`](pipeline/) | Lanzadores end-to-end (glxgears, Minecraft dos ventanas, Minecraft ventana única). |
| [`benchmarks/`](benchmarks/) | Experimentos con medidas reales. Incluye [`viability/`](benchmarks/viability/): estudio de viabilidad Fase 1 (580 mediciones, 6 dispositivos × 6 modelos × cargas). |
| [`phase2/`](phase2/) | Fase 2: comparativa nativo vs híbrido (render bajo + upscaling IA) con PSNR/SSIM. |
| [`results/`](results/) | CSV, capturas, muestras (`sample_frames/`) y el subconjunto presentado al tutor (`viability_submission/`). |
| [`models/`](models/) | Modelos de superresolución (OpenVINO IR, ONNX, .pb, .pth). |
| [`docs/`](docs/) | Justificación wrapper vs VirtualGL (medida) y contexto del proyecto. |
| [`virtualgl/`](virtualgl/) | Alternativa evaluada: VirtualGL con hook de captura propio. No adoptada — ver docs. |
| [`archive/`](archive/) | Prototipos tempranos y scripts de **simulación** (no citar como medidas). |

Cada carpeta tiene su propio `README.md` con el detalle archivo a archivo.

## Instalación

```bash
# Dependencias de sistema
sudo apt install build-essential mesa-utils xvfb intel-opencl-icd clinfo

# Entorno Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Interceptor
./capture/build.sh
```

## Uso rápido

```bash
# Demo completa: Xvfb + glxgears interceptado + superresolución OpenVINO en iGPU
./pipeline/run_hybrid_pipeline.sh

# Manual: capturar cualquier app OpenGL...
LD_PRELOAD=$PWD/capture/wrapper_swapbuffers_shm.so glxgears
# ...y en otra terminal, procesar:
python3 processing/upscale_display.py

# Experimento de barrido de resoluciones
cd benchmarks && ./run_experiment1.sh
```

## Rendimiento medido (RTX 5060 + Intel iGPU)

| Componente | Latencia | Notas |
|---|---|---|
| Captura (interceptor propio) | ~1,5 ms/frame a 1080p | 639 FPS de captura sostenidos |
| Transferencia shm | ~0,1 ms | copia única, header de sincronización |
| Superresolución (OpenVINO iGPU) | 10–15 ms | cuello de botella del pipeline |

La elección del interceptor propio frente a VirtualGL está justificada con
mediciones en
[`docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md`](docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md)
(2,7–3,2× menos overhead de captura).

## Solución de problemas

| Problema | Solución |
|---|---|
| shm residual tras un cuelgue | `rm -f /dev/shm/framebuffer_shared` |
| OpenCL/iGPU no detectada | `sudo apt install intel-opencl-icd && clinfo \| grep Intel` |
| El lector ve basura | Comprobar que lector y wrapper usan el mismo formato (header vs legacy, ver `capture/README.md`) |
| Monitorizar GPUs | `intel_gpu_top` (iGPU) / `nvidia-smi -l 1` (dGPU) |
