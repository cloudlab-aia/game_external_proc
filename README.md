# Sistema híbrido GPU para superresolución basada en IA en videojuegos (TFG)

Arquitectura híbrida dGPU+iGPU para videojuegos: el juego se ejecuta en una
**pantalla virtual oculta** renderizado por la **dGPU NVIDIA**, cada frame se
captura de la VRAM de forma transparente (sin modificar el juego) y se
transfiere por memoria compartida a la **iGPU Intel**, que lo reconstruye a
resolución completa con un modelo de superresolución (FSRCNN/OpenVINO). El
usuario ve una única ventana con el resultado y juega a través de ella.

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐
│ Juego (oculto)   │   │ Memoria          │   │ Superresolución  │   │  Ventana     │
│ dGPU + Xvfb :2   │──▶│ compartida       │──▶│  iGPU Intel      │──▶│  única       │
│ captura sin      │   │ /dev/shm (~0,3ms)│   │  OpenVINO        │   │  + input     │
│ presentación     │   │                  │   │                  │   │  reenviado   │
└──────────────────┘   └──────────────────┘   └──────────────────┘   └──────────────┘
```

Piezas clave: interposición de `glXSwapBuffers` vía `LD_PRELOAD` (con soporte
para GLFW/LWJGL3, probado con Minecraft 1.20 + shaders), renderizado en la
pantalla oculta por PRIME offload, modo de **captura sin presentación**
(`CAPTURE_SKIP_PRESENT`, elimina el cuello de botella del display virtual) y
overlay con reenvío de teclado y ratón (XTEST).

## Demo en un comando

```bash
./pipeline/run_arquitectura_final.sh
```

Levanta la pantalla virtual, abre el launcher visible (inicia sesión y dale a
Jugar), verifica el enganche, ajusta el render a 640×360 y abre el overlay
jugable a 1080p con FSRCNN x3 en la iGPU. Salir: F12. Modos:

```bash
GAME_W=480 GAME_H=270 FSRCNN_SCALE=4 ./pipeline/run_arquitectura_final.sh  # rendimiento
GAME_W=960 GAME_H=540 FSRCNN_SCALE=2 ./pipeline/run_arquitectura_final.sh  # calidad
```

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| [`capture/`](capture/) | Interceptor C (`LD_PRELOAD` sobre `glXSwapBuffers`) → shm con header, modo captura sin presentación, filtro por proceso; interposer de lanzamiento que manda solo el juego a la pantalla oculta. |
| [`processing/`](processing/) | Superresolución en la iGPU (FSRCNN/OpenVINO, sisr-1032, ONNX, Real-ESRGAN) y overlay de ventana única con reenvío de entrada. |
| [`pipeline/`](pipeline/) | Lanzadores end-to-end, de la demo con glxgears a la arquitectura final (`run_arquitectura_final.sh`). |
| [`experiments/`](experiments/) | Scripts de la campaña experimental de la memoria (Exps. 5–11): carga de dGPU, peso de la IA, barridos de resolución, matriz de calidad, latencia por componente. |
| [`benchmarks/`](benchmarks/) | Benchmarks base (captura, inferencia, FPS de render) y [`viability/`](benchmarks/viability/): estudio de viabilidad Fase 1 (580 mediciones, 6 dispositivos × 6 modelos × cargas). |
| [`phase2/`](phase2/) | Fase 2: comparativa nativo vs híbrido (render bajo + upscaling IA) con PSNR/SSIM. |
| [`results/`](results/) | Datos medidos de todos los experimentos, con su correspondencia experimento a experimento con la memoria. |
| [`models/`](models/) | Modelos de superresolución (OpenVINO IR, ONNX, .pb, .pth). |
| [`docs/`](docs/) | Justificación medida del wrapper propio frente a VirtualGL, parche de VirtualGL evaluado y estudio de la pantalla oculta. |
| [`archive/`](archive/) | Prototipos tempranos y scripts de **simulación** (no son medidas; no citar como resultados). |

Cada carpeta tiene su propio `README.md` con el detalle archivo a archivo.

## Instalación

```bash
# Dependencias de sistema
sudo apt install build-essential mesa-utils xvfb intel-opencl-icd clinfo xdotool

# Entorno Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Interceptor
./capture/build.sh
```

## Uso manual

```bash
# Capturar cualquier app OpenGL...
LD_PRELOAD=$PWD/capture/wrapper_swapbuffers_shm.so glxgears
# ...y en otra terminal, reconstruir y mostrar:
python3 processing/upscale_display.py

# Medir los FPS de render en cualquier momento (contador de la shm)
python3 benchmarks/render_fps.py --seconds 8 --interval 8
```

## Resultados principales (RTX 5060 + Intel Core Ultra 7 265K)

Medidos sin sincronización vertical; protocolo completo en
[`results/experiments/expNOVSYNC_RESUMEN.md`](results/experiments/expNOVSYNC_RESUMEN.md).

| Resultado | Valor |
|---|---|
| Captura + transferencia + preproceso | < 1 ms/frame |
| Latencia del pipeline completo (640×360 → x3 → 1080p) | ~35 ms (inferencia 52 %, postproceso 31 %) |
| Minecraft + shaders exigentes, salida 1080p | nativa 44 FPS → híbrida 51 FPS |
| Captura sin presentación en la pantalla oculta | 13 → 44,6 FPS (iguala a la presentación por hardware) |
| Híbrida vs dedicada con la dGPU como cuello de botella | gana en fluidez desde 2× el coste de FSRCNN, hasta +32 % |

La elección del interceptor propio frente a VirtualGL está justificada con
mediciones en
[`docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md`](docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md)
(2,7–3,2× menos overhead de captura).

## Solución de problemas

| Problema | Solución |
|---|---|
| shm residual tras un cuelgue | `rm -f /dev/shm/framebuffer_shared` |
| OpenCL/iGPU no detectada | `sudo apt install intel-opencl-icd && clinfo \| grep Intel` |
| El launcher no vuelve a abrir | `rm ~/.minecraft/webcache2/Singleton*` |
| El juego se abre en Wayland (GLFW 65548) | lanzar con `env -u WAYLAND_DISPLAY` |
| La captura se congela con la ventana tapada | mantener visible la ventana del juego (el compositor Wayland detiene los swaps de ventanas X11 ocluidas) |
| El lector ve basura | comprobar que lector y wrapper usan el mismo formato (header vs legacy, ver `capture/README.md`) |
| Monitorizar GPUs | `intel_gpu_top` (iGPU) / `nvidia-smi -l 1` (dGPU) |
