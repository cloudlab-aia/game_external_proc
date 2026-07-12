# Campaña sin VSYNC: protocolo y resultados (2026-07-09/10)

Re-ejecución de los experimentos de la rama con presentación por hardware,
tras detectar que las medidas anteriores estaban limitadas por VSYNC
(cuantización a submúltiplos de 60 Hz) y, en el caso del Exp 6 antiguo,
contaminadas por procesos en segundo plano. **Los datos antiguos de esa rama
quedan invalidados y no deben citarse.**

## Condiciones comunes

- Minecraft 1.20.1 (Fabric: Iris 1.7.2 + Sodium 0.5.11) + shaders Photon,
  ajustes del shader al máximo. Mismo mundo, misma posición, cámara quieta.
- **VSync: OFF** y **Max Framerate: Unlimited** en las opciones de vídeo,
  más `__GL_SYNC_TO_VBLANK=0` en el entorno (refuerzo para el driver NVIDIA).
- Juego en modo ventana (F11) en la sesión real `:1`, renderizado por la
  dGPU (RTX 5060), capturado con el wrapper (`FRAME_CAPTURE_EXE=java`).
- Resolución de render fijada con `xdotool windowsize` y **verificada
  leyendo el header de la memoria compartida** tras cada cambio (lección:
  con el juego a pantalla completa el resize no aplica y se mide otra cosa).
- FPS de render = contador de secuencia del buzón compartido
  (`benchmarks/render_fps.py`), ventanas de medida de 6–10 s.
- Utilización de la dGPU muestreada con `nvidia-smi`.
- La ventana del juego debe permanecer **visible y sin tapar**: el
  compositor Wayland congela los swaps de ventanas X11 ocluidas
  (throttling de Xwayland) y la captura se detiene.

## Ficheros

| Fichero | Experimento |
|---|---|
| `fps_resolution_sweep_novsync.csv` | Barrido de resolución de render (header verificado) |
| `exp6_trio_novsync.csv` | Nativa vs híbrida vs dedicada (640×360 x3 → 1080p) |
| `expF_weight_novsync.csv` | Peso de la IA ×1…×8, híbrida vs dedicada |
| `latency_components.csv` | Latencia por componente del pipeline |

## Resultados clave

1. **Barrido:** 60,2 FPS (426×240) → 44,2 FPS (1080p). El escalado con la
   resolución existe pero es suave (1,36×): con Photon al máximo domina un
   coste fijo por frame (~16 ms). Sin shaders, 1080p = 219 FPS.
2. **Trío (salida 1080p):** nativa 44,2 / híbrida 51,0 / dedicada 51,2.
   Con FSRCNN real (ligero) híbrida ≈ dedicada; mejora 1,15× sobre nativa.
3. **Peso de la IA:** la híbrida gana en fluidez desde ×2 (33,5 vs 30,8) y
   el margen crece con el peso (×8: 22,8 vs 17,3, +32%). El juego también
   cae en la híbrida al crecer el peso (presupuesto de potencia compartido
   CPU/iGPU en el package, la iGPU cargada resta clocks a la CPU).
4. **Latencia por componente** (640×360 x3 → 1080p, FSRCNN iGPU):
   lectura 0,25 / preproceso 0,29 / **inferencia 18,4** / **postproceso 11,1**
   / presentación 5,0 → total 35,1 ms (~28 FPS de capacidad). La inferencia
   es el 53% del total, no el 99%: el postproceso (croma+merge a 1080p) pasa
   a ser el segundo coste y es optimizable (moverlo a GPU).

## Validación cruzada

- Referencia hardware 44,2 FPS ≈ 44,6 FPS del camino skip-present
  (medido semanas antes, sin VSYNC posible al no haber swap): dos vías
  independientes convergen.
- Entregados ≈ min(FPS render, FPS inferencia) en todas las configuraciones.
- Los datos de la pantalla virtual con captura sin presentar (Exp 10 /
  expG_xvfb_skip) **no** se ven afectados por el VSYNC y siguen vigentes.

## Incidencias documentadas

- **Bug de captura con FBO (arreglado):** Photon/Iris puede dejar un FBO
  intermedio enlazado en el swap; `glReadPixels` leía ese buffer vacío y el
  wrapper descartaba los frames como "negros". Fix: forzar
  `glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)` antes de leer y restaurar
  después (`capture/wrapper_swapbuffers_shm.c`).
- **Throttling de Xwayland:** ventana del juego tapada ⇒ 0 FPS de captura.
  Protocolo: mantenerla visible durante toda la medida.
