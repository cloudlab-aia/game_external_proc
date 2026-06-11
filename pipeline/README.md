# pipeline/ — Lanzadores del sistema completo

Scripts que orquestan captura + procesado IA de extremo a extremo.

## Archivos

| Archivo | Qué lanza |
|---|---|
| `run_hybrid_pipeline.sh` | **Demo completa del TFG.** Compila el interceptor, levanta Xvfb en `:2`, lanza glxgears 1920×1080 con `LD_PRELOAD`, y arranca `processing/upscale_display.py` (OpenVINO en iGPU) con la ventana en el display real `:1`. Ctrl+C o tecla `q` para parar todo. |
| `run_ai_pipeline.sh` | Variante que usa `processing/upscale_openvino.py` (Real-ESRGAN ONNX). Comprueba wrapper, script y modelo antes de lanzar. |
| `run_minecraft_pipeline.sh` | **Pipeline con juego real.** Lanza el launcher de Minecraft con el interceptor (filtrado al proceso java del juego vía `FRAME_CAPTURE_EXE`), sin `WAYLAND_DISPLAY` para forzar GLFW a X11/GLX, y el upscaler OpenVINO en paralelo. |

## Configuración relevante (`run_hybrid_pipeline.sh`)

- `VIRTUAL_DISPLAY=":2"` — display Xvfb donde corre el juego
- `REAL_DISPLAY=":1"` — sesión X real donde aparece la ventana procesada
- `IGPU_MONITOR_X=1920` — offset horizontal del monitor de la iGPU
- `APP_TO_RUN` — aplicación OpenGL a capturar (por defecto glxgears)

## Problemas comunes

- shm residual de una ejecución anterior: `rm -f /dev/shm/framebuffer_shared`
- El interceptor no compila: ejecutar `../capture/build.sh` a mano y mirar el error
- Ventana no aparece: comprobar `DISPLAY` y `XAUTHORITY`
