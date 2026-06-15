# Bitácora de desarrollo — Pipeline híbrido de superresolución

Registro cronológico de los pasos realizados sobre el sistema de captura de
frames + upscaling por IA en arquitectura híbrida dGPU/iGPU. Sesión de trabajo
iniciada el 2026-06-11. Cada bloque corresponde a uno o varios commits.

Hardware de referencia: NVIDIA RTX 5060 (dGPU), Intel Core Ultra 7 265K con
Intel Graphics (iGPU) y NPU, Ubuntu 25.10, sesión KDE Wayland.

---

## 1. Evaluación experimental: interceptor propio vs. VirtualGL

**Objetivo:** decidir, con datos, el mecanismo de captura de frames.

- Se portó el bloque de captura (shm con header) al hook `glXSwapBuffers` de
  VirtualGL (`virtualgl/server/faker-glx.cpp`, función `hybridCaptureToShm`),
  sustituyendo un prototipo previo que volcaba un PPM a disco por frame.
- Se compiló VirtualGL desde fuente (resolviendo dependencias TurboJPEG, XCB,
  OpenCL sin privilegios de root) y se eliminó un `find_package(CUDA REQUIRED)`
  erróneo del CMake.
- Se midió ambas vías con el **mismo** bloque de captura sobre glxgears, sin
  vsync, en la RTX 5060.

**Resultado (FPS de captura):**

| Resolución | Baseline | Interceptor propio | VirtualGL mod. | Ventaja |
|---|---|---|---|---|
| 640×360 | 33 551 | 4 414 | 1 387 | 3,2× |
| 1280×720 | 30 950 | 1 311 | 477 | 2,7× |
| 1920×1080 | 21 469 | 639 | 222 | 2,9× |

**Decisión:** interceptor propio (2,7–3,2× menos overhead, sin trabajo
redundante de readback/transporte, sin fork de 600 ficheros que mantener).
VirtualGL queda documentado como alternativa evaluada.
Detalle: `docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md`.

---

## 2. Reorganización del repositorio

Se reestructuró el repo a una organización por responsabilidades:
`capture/`, `processing/`, `pipeline/`, `benchmarks/`, `results/`, `models/`,
`docs/`, `virtualgl/`, `archive/`, con un `README.md` por carpeta. Se separó
el material de **medición real** del de **simulación** (a `archive/`, para no
citarlo nunca como medida). Se añadió `requirements.txt` y se eliminaron
entornos virtuales, clones externos y binarios regenerables (de ~4,5 GB a
~340 MB).

---

## 3. Soporte de captura para juegos reales (Minecraft)

Minecraft (≥1.13, LWJGL3/GLFW) no resuelve los símbolos GL por enlace
dinámico normal, sino con `dlopen`/`dlsym`/`glXGetProcAddressARB`, lo que
esquiva un `LD_PRELOAD` clásico. Se amplió el interceptor
(`capture/wrapper_swapbuffers_shm.c`) para cubrir las tres rutas de
resolución de símbolos.

Problemas resueltos al inyectar a través del launcher:
- **SIGBUS en el juego:** launcher y juego heredaban el wrapper y escribían en
  la misma shm con tamaños distintos; el `ftruncate` de uno invalidaba el mapeo
  del otro. Solución: filtro `FRAME_CAPTURE_EXE=java` (solo captura el proceso
  del juego).
- **Tamaño de frame errático:** Minecraft cambia `glViewport` varias veces por
  frame. Solución: tomar el tamaño de `glXQueryDrawable` (ventana), no del
  viewport.

Resultado: captura de Minecraft real funcionando (verificado a 854×505,
~30–35 FPS de captura).

---

## 4. Vía jugable: FSRCNN sobre OpenVINO en la iGPU

El modelo de referencia (`single-image-super-resolution-1032`) daba ~63 ms/
frame (16 FPS): injugable. Búsqueda del mejor motor/modelo sobre un frame real
de Minecraft:

| Vía | Latencia | FPS |
|---|---|---|
| sisr-1032 (OpenVINO iGPU) | 63 ms | 16 |
| FSRCNN vía OpenCV/OpenCL | 95–350 ms | 3–10 (backend roto en esta iGPU) |
| **FSRCNN x4 → OpenVINO IR (iGPU)** | **13 ms** | **75** |
| FSRCNN x2 → OpenVINO IR (iGPU) | 34 ms | 30 |

**Hallazgo:** convertir FSRCNN a OpenVINO IR multiplica los FPS (mismo modelo,
mismos pesos, misma calidad) porque OpenVINO recompila con kernels optimizados
para Intel. Se corrigió además un bug de postprocesado del modelo de
referencia (devuelve un **residuo** que hay que sumar a la bicúbica; sin eso la
salida era casi negra).

---

## 5. Modo ventana única (opción B) — jugar sobre el resultado

Objetivo: una sola ventana visible, jugable, mostrando la salida reescalada
por IA, sin modificar el juego.

Implementación (`processing/display_overlay.py`,
`pipeline/run_minecraft_single_window.sh`): el juego corre debajo (render en
dGPU) y un overlay fullscreen (pygame) muestra el frame reescalado en la iGPU.
Problemas de integración con KDE Wayland resueltos en orden:

1. **Ratón no funcionaba:** el overlay se comía los clics. Solución:
   *click-through* con región de entrada vacía de XShape — el puntero atraviesa
   hasta el juego.
2. **El juego se pausaba:** al mapear el overlay, KDE le daba foco y Minecraft
   pausaba al perderlo. Solución: overlay tipo *dock*, no-focusable
   (`_NET_WM_WINDOW_TYPE_DOCK` + `input=False`).
3. **Backend de ventana:** se fuerza `QT_QPA_PLATFORM=xcb` (OpenCV no trae
   plugin Qt para Wayland).

Resultado: **Minecraft jugable en ventana única**, input nativo (teclado al
juego, mouse-look por la captura de puntero del propio juego), viendo la
versión reescalada a 1080p.

---

## 6. Demo de baja resolución (la tesis en acción)

`pipeline/run_minecraft_single_window.sh` arranca el juego en ventana
**480×270** (la dGPU renderiza pocos píxeles) y FSRCNN reconstruye a 1080p. Se
resolvió la captura del puntero con una cuenta atrás antes de cubrir la
pantalla. Demuestra el objetivo del proyecto: **render de bajo coste en dGPU +
reconstrucción IA en acelerador secundario.**

---

## 7. Consolidación de repositorios

Se unificó el trabajo en este repositorio como hogar único, importando del
repo previo `TFG_CODE` (que se presentó al tutor):

- `benchmarks/viability/` — estudio de viabilidad (Fase 1): 580 mediciones,
  6 dispositivos × 6 modelos × resoluciones × 4 cargas. Sus CSVs.
- `results/viability_submission/` — subconjunto curado presentado al tutor
  (gráficas, comparativas, resúmenes). Se excluyeron los ~1 GB de frames
  crudos.
- `phase2/` — framework de comparación nativo vs híbrido
  (`hybrid_pipeline.py`, `compare_frames.py`, `simulate_game.py`).
- `models/openvino_ir/` — FSRCNN IR de entrada flexible (modelos canónicos).
- `results/sample_frames/` — capturas reales de Minecraft a varias
  resoluciones.

Se corrigió un bug latente NCHW/NHWC en `phase2/hybrid_pipeline.py` (la salida
del IR es NCHW `(1,1,H,W)`; el indexado antiguo aplastaba los frames a 1 px de
alto). Cadena de Fase 2 verificada de extremo a extremo sobre un frame real de
Minecraft: 480×270→1080p, ~60 FPS, PSNR 35,1 dB / SSIM 0,93 vs bicúbico.

---

## 8. Unificación de modelos

Se eliminó la duplicidad de modelos IR. Toda la pipeline (tiempo real,
Fase 2, viabilidad) usa ahora los mismos `models/openvino_ir/FSRCNN_x{2,3,4}`
de entrada flexible; la vía en tiempo real los reshapea a entrada fija al
cargar (sin pérdida de velocidad, ~66 FPS en iGPU). Una sola fuente de verdad.

**Confirmado:** la demo de Minecraft en tiempo real corre con la configuración
adoptada del estudio de viabilidad — **iGPU + OpenVINO + FSRCNN IR**.

---

## 9. Pipeline unificado con pantalla virtual real (jugable)

Se completó la arquitectura del enunciado de extremo a extremo: el juego
corre en una pantalla virtual oculta, renderizado por la dGPU, y solo se ve
el resultado reescalado en una ventana real jugable.

```
launcher normal (:1)
  └─[capture/game_launch_interposer.so]─> solo el proceso del juego va a
       pantalla virtual Xvfb (:2), render dGPU vía VirtualGL, captura a shm
         └─> iGPU FSRCNN/OpenVINO ─> processing/display_overlay_forward.py
              muestra en ventana real (:1) + reenvía teclado/ratón a (:2)
```

Piezas y problemas resueltos (todo en KDE Wayland):
- **Interceptor de lanzamiento** (`game_launch_interposer.c`): se precarga en
  el launcher, intercepta `execve`/`posix_spawn`… y reescribe el entorno SOLO
  del proceso del juego (argv con `net.minecraft`) para mandarlo a la pantalla
  virtual con VirtualGL. El launcher se usa con normalidad.
- **Compatibilidad VirtualGL ↔ Minecraft**: 1.21.2 (motor blaze3d/GL moderno)
  crashea en el driver NVIDIA bajo VGL; **1.12.2 (OpenGL clásico) funciona**.
  Documenta el límite de VGL con motores GL modernos.
- **Foco**: sin gestor de ventanas en Xvfb el juego no recibía foco y se
  quedaba en pausa; el overlay fija el foco (`XSetInputFocus`) y lo re-afirma.
- **Reenvío de ratón consciente del modo**: en partida Minecraft recoloca el
  puntero al centro y lee deltas → se reenvía movimiento **relativo**; en
  menús se reenvía posición **absoluta** (apuntar botones). El modo se detecta
  sondeando el grab del puntero en `:2`.
- **Cursor sintético**: `glReadPixels` no captura el cursor del servidor X, así
  que se dibuja en el overlay según la posición reenviada (solo en menús).

Resultado: Minecraft 1.12.2 jugable, cámara suave y menús navegables, viendo
la salida IA a 1080p, con el juego renderizando oculto en la dGPU.

## Estado actual

Funciona y está verificado:
- Captura de glxgears y Minecraft real (interceptor propio).
- Upscaling FSRCNN/OpenVINO en iGPU en tiempo real (~66 FPS).
- Minecraft jugable en ventana única con la salida reescalada.
- **Pantalla virtual real + juego jugable** (Xvfb + VirtualGL + reenvío de
  input): la arquitectura completa del enunciado de extremo a extremo.
- Framework de Fase 2 operativo (verificado con frames reales).
- Estudio de viabilidad (Fase 1) integrado.

Pendiente:
- **Fase 2 con datos reales**: comparativa nativo vs híbrido vs bicúbico a
  varias resoluciones (siguiente paso).
- **Latencia end-to-end** medida (dGPU genera → se muestra): métrica central
  del enunciado, aún sin medir de forma integrada.
- **Pantalla virtual real** (render dGPU headless): el enunciado lo pide; ahora
  el juego corre en `:1` tapado, no en pantalla virtual.
- **NPU** (Core Ultra 7 265K la tiene): trabajo futuro del enunciado.
- Rehacer la memoria para reflejar estos avances.

## Commits de esta etapa

```
ce83484  Evaluate VirtualGL capture path against custom wrapper with real benchmark
6bdc629  Reorganize repository into thesis structure
0b5c0c9  Support real games: Minecraft capture working end to end
80682bb  Add playable FSRCNN/OpenVINO upscaler (~75 FPS on iGPU)
2556068  Add single-window mode: fullscreen AI-upscaled overlay over the game
6555e16  Make overlay click-through so mouse reaches the game
d3376c6  Keep overlay from stealing focus so the game does not pause
1eefcc9  Single-window: run the game at low resolution for a real upscaling demo
7956a53  Merge viability study and phase 2 framework from the prior repo
a3b2a32  Unify on the canonical flexible FSRCNN IR models
```
