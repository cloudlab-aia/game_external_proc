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

## Barrido nativo por resolucion de salida (2026-07-17)

Complemento del barrido hibrida vs dedicada sobre pantalla virtual con
captura sin presentar: FPS del juego renderizando NATIVO (sin sistema de
super-resolucion, sin consumidor) a cada resolucion de salida del Exp G.
Mismo camino (Xvfb 4K + PRIME + CAPTURE_SKIP_PRESENT=1, sin VSync, misma
escena fija), script `experiments/run_native_output_sweep.sh`, 8 s de
medida por punto tras estabilizacion, resolucion efectiva verificada en
la cabecera del shm. CSV: `expG_native_output.csv`.

| Salida | FPS | | Salida | FPS |
|---|---|---|---|---|
| 640x360 | 52.6 | | 1920x1080 | 43.4 |
| 960x540 | 51.3 | | 2560x1440 | 34.5 |
| 1280x720 | 47.5 | | 2562x1440 | 34.7 |
| 1440x810 | 45.1 | | 2880x1620 | 33.9 |
| 1708x960 | 45.4 | | 3416x1920 | 29.6 |
| | | | 3840x2160 | 25.7 |

Validacion cruzada: 1080p nativo = 43.4 FPS, consistente con los
44.2/44.6 FPS de las tandas anteriores. Lectura: la hibrida se mantiene
en 54-62 FPS en todo el barrido mientras el nativo cae con la salida;
a 4K la hibrida casi duplica al nativo (54.9 vs 25.7, +29 FPS).
Graficas regeneradas con la recta nativa: `plots/expG_game_x{2,3,4}_xvfb_skip.png`.

## Verificacion de la no-monotonia del Exp G (2026-07-17)

Los puntos hibrida x3/x4 en 640x360 y 854x480 mostraban una subida no
monotona en la campana original (55.7 -> 58.2 en x4). Re-medidos con dos
repeticiones por punto (misma sesion, escena distinta de la original):
x3: 45.8/45.9 -> 42.9/43.5; x4: 45.1/45.0 -> 43.9/44.1. Comportamiento
monotono decreciente y repetible (<0.5 FPS entre repeticiones). La
subida original era variabilidad entre sesiones, no un efecto
sistematico. Parrafo del analisis corregido en la memoria.
