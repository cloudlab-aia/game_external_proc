# Exp H — "Capturar sin presentar": pantalla virtual GPU-bound

Hipótesis: el cuello de la pantalla virtual (Xvfb) es la **presentación software**
(la copia dGPU→Xvfb por CPU en cada `glXSwapBuffers`). Si el wrapper captura el
frame de la VRAM (`glReadPixels`) y **NO llama al swap real**, se evita esa copia:
la dGPU renderiza el siguiente frame de inmediato (GPU-bound) y el frame queda
oculto de verdad (nunca se presenta). Realiza la arquitectura del enunciado
(render en pantalla virtual + captura de VRAM + IA en iGPU) SIN el penalti
copy-bound.

Implementación: flag `CAPTURE_SKIP_PRESENT=1` en `capture/wrapper_swapbuffers_shm.c`
(tras capturar con éxito, `return` sin llamar a `real_glXSwapBuffers`).

## Validación con glxgears (Xvfb :2, PRIME, 1280x720)

| Modo | FPS de render | GPU |
|---|---|---|
| Normal (presenta a Xvfb) | 62 | 15 % (copy-bound) |
| **CAPTURE_SKIP_PRESENT** | **1279** | 36 % |

**20× más rápido.** La captura sigue funcionando (el buzón avanza a 1279 FPS).
Al saltarse la copia software, el render pasa a GPU-bound. **Hipótesis validada.**

## Implicación

Es la vía que podría hacer la arquitectura híbrida real (pantalla virtual oculta)
también **rápida** (GPU-bound), y por tanto donde la ventaja híbrida (IA en iGPU,
dGPU libre) sí se materializaría — a diferencia del Xvfb normal (copy-bound, donde
no gana, ver Exp F/G).

## Confirmado con Minecraft + Photon (2026-07-02)

Lanzando el launcher DIRECTAMENTE en `:2` (sin interposer frágil): `env -u
WAYLAND_DISPLAY DISPLAY=:2 LD_PRELOAD=wrapper FRAME_CAPTURE_EXE=java
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia
CAPTURE_SKIP_PRESENT=1 minecraft-launcher`. El launcher y el juego heredan `:2` +
X11 + wrapper + skip-present; el filtro `FRAME_CAPTURE_EXE=java` hace que el
wrapper solo capture el juego (no la UI del launcher). Se navega el launcher/menús
por screenshots (`import -display :2 -window root` / buzón shm) + xdotool.

Resultado — Minecraft + Photon en el mundo "Shaders", pantalla oculta `:2`:

| 1080p Photon | FPS render | GPU |
|---|---|---|
| Xvfb NORMAL (copy-bound) | ~13 | bajo |
| `:1` hardware (GPU-bound) | ~43 | alto |
| **Xvfb + SKIP-PRESENT (oculto)** | **44,6** | **85 %** |

**El skip-present hace la pantalla virtual oculta GPU-bound (85 % GPU), igualando
al hardware, 3,4× el Xvfb normal.** Resuelve el conflicto oculto+rápido+capturable
que se creía imposible (ver docs/INVESTIGACION_PANTALLA_OCULTA): no hace falta 2ª
GPU ni arranque headless — basta con capturar de VRAM y NO presentar.

Implicación: la arquitectura híbrida REAL (pantalla virtual oculta) es viable y
rápida. Pendiente: repetir híbrida vs dedicada en este camino (debería ganar la
híbrida, al ser GPU-bound).

## Experimento híbrida vs dedicada en la pantalla oculta rápida (Xvfb+SKIP)

Barrido de resoluciones × escala (Exp G) en los 3 caminos, margen de FPS de juego
de la híbrida (IA iGPU) sobre la dedicada (IA dGPU):

| Camino | Oculto | Rápido | Híbrida gana |
|---|---|---|---|
| Xvfb normal (copy-bound) | sí | no | 0/15 (pierde siempre) |
| :1 hardware (GPU-bound) | no (tapado) | sí | 6/15 (a resoluciones altas) |
| **Xvfb + SKIP-PRESENT** | **sí** | **sí** | **15/15** (margen hasta +26,6 FPS) |

En Xvfb+SKIP la híbrida gana en las 15 combinaciones y el margen crece con la
resolución (a mayor render, la IA en la dGPU roba más → la dedicada se hunde;
la híbrida mantiene la dGPU libre). Datos: expG_resolution_xvfb_skip.csv.

**Conclusión:** el "capturar sin presentar" hace viable la arquitectura híbrida
REAL (pantalla virtual oculta), rápida (GPU-bound) y con la ventaja híbrida
demostrada en todo el rango. Resuelve el conflicto oculto+rápido+capturable.
