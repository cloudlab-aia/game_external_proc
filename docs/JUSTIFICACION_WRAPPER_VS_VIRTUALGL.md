# Justificación experimental: interposer propio vs. VirtualGL modificado

**Fecha:** 2026-06-11
**Hardware:** NVIDIA GeForce RTX 5060 (render), display X11 `:1` con direct rendering
**Software:** Ubuntu (kernel 6.17), glxgears (mesa-utils), VirtualGL compilado desde `virtualgl/` con hook de captura propio

## 1. Pregunta

¿Qué mecanismo de captura de frames conviene como base del pipeline híbrido
dGPU→iGPU: un interposer `LD_PRELOAD` mínimo propio
(`iframe_capture/wrapper_swapbuffers_shm.c`, ~150 líneas) o VirtualGL
modificado (fork de ~600 ficheros con hook en
`virtualgl/server/faker-glx.cpp`)?

Nota conceptual: ambos usan el **mismo mecanismo** de interposición
(`LD_PRELOAD` sobre `glXSwapBuffers`). `vglrun` precarga `libvglfaker.so`
igual que nuestro wrapper. La diferencia es lo que el framework hace además
de capturar: VirtualGL redirige el render a Pbuffers, hace readback con PBOs
y transporta el frame al servidor X de destino.

## 2. Metodología

Para que la comparación sea justa, **ambas vías ejecutan un bloque de captura
idéntico** dentro del hook de `glXSwapBuffers`:

```
glFinish() → glReadPixels(RGBA) → escritura en /dev/shm/framebuffer_shared
con header de 16 bytes (uint32: width, height, seq, ready) + flip vertical
```

En VirtualGL este bloque se portó como `hybridCaptureToShm()` en
`server/faker-glx.cpp` (sustituyendo al prototipo anterior, que volcaba un
PPM a disco por frame). El formato shm es idéntico, por lo que los lectores
Python (`benchmark_models.py`, `upscale_display.py`) funcionan sin cambios
con cualquiera de las dos vías.

Medición (`bench_capture.py`):
- **FPS de aplicación**: salida nativa de glxgears (media de muestras de 5 s).
- **FPS de captura**: incremento del contador `seq` del header shm por
  segundo, medido por un proceso lector independiente.
- vsync desactivado (`__GL_SYNC_TO_VBLANK=0`, `vblank_mode=0`).
- Warmup de 4 s, ventana de medida de 10 s por caso.
- VirtualGL en modo local (`DISPLAY=:1`, `VGL_DISPLAY=:1`), es decir, con su
  pipeline completo de readback y transporte activo.

## 3. Resultados

| Resolución | Baseline (sin captura) | Wrapper propio | VirtualGL mod. | Ventaja wrapper |
|---|---|---|---|---|
| 640×360 | 33 551 FPS | 4 414 FPS | 1 387 FPS | **3,2×** |
| 1280×720 | 30 950 FPS | 1 311 FPS | 477 FPS | **2,7×** |
| 1920×1080 | 21 469 FPS | 639 FPS | 222 FPS | **2,9×** |

(FPS de captura; los FPS de aplicación coinciden en ±2 %, como cabe esperar
porque la captura es síncrona dentro de `glXSwapBuffers`.)

Coste por frame añadido sobre el baseline (1/FPS − 1/FPS_baseline):

| Resolución | Wrapper propio | VirtualGL mod. | Sobrecoste extra de VGL |
|---|---|---|---|
| 640×360 | ~0,20 ms | ~0,69 ms | +0,5 ms |
| 1280×720 | ~0,74 ms | ~2,11 ms | +1,4 ms |
| 1920×1080 | ~1,54 ms | ~4,49 ms | +3,0 ms |

## 4. Análisis

1. **Ambas vías superan holgadamente el objetivo de 60 FPS** a 1080p
   (639 y 222 FPS). El cuello de botella del pipeline completo es la
   inferencia IA (10–15 ms), no la captura. La elección, por tanto, no la
   decide solo el rendimiento bruto.
2. **VirtualGL añade ~3 ms/frame extra a 1080p** porque, además de nuestra
   captura, ejecuta su propio pipeline de readback (PBO) y transporte al
   servidor X. Ese trabajo es redundante para nuestro caso de uso: no
   necesitamos transporte remoto.
3. **Coste de ingeniería**: la vía VirtualGL exige mantener un fork de ~600
   ficheros C++, una cadena de build con CMake y dependencias (TurboJPEG,
   XCB, OpenCL) e instalación en el sistema. El wrapper son ~150 líneas
   propias compiladas con una orden de gcc.
4. **Defendibilidad**: el wrapper es código íntegramente propio, explicable
   línea a línea ante el tribunal; el hook en VirtualGL vive dentro de un
   `glXSwapBuffers` de 2 400 líneas ajeno.

## 5. Amenazas a la validez (declarar en la memoria)

- glxgears es una carga trivial; con un juego real el baseline sería mucho
  menor y el peso relativo del overhead de captura, menor en ambas vías.
- En la integración actual el hook de VirtualGL hace un `glReadPixels`
  **adicional** al readback interno de VGL. Una integración profunda
  (capturar del buffer ya leído por `vw->readback()`) reduciría el
  sobrecoste de VGL; no se exploró porque exigiría modificar el núcleo del
  faker.
- A 1920×1080 el gestor de ventanas recorta la ventana a 1920×1008
  (decoraciones/panel); afecta por igual a ambas vías.

## 6. Conclusión

Se adopta el **interposer propio** como mecanismo de captura del pipeline:

- 2,7–3,2× menos overhead de captura que VirtualGL modificado (mismo bloque
  de captura, misma máquina, mismo benchmark).
- Sin trabajo redundante (readback/transporte de VGL que el caso de uso no
  necesita).
- Sin fork de terceros que mantener ni explicar.

VirtualGL queda documentado como **alternativa evaluada experimentalmente**
(no descartada a priori), con su prototipo funcional en
`virtualgl/server/faker-glx.cpp` como evidencia de la exploración.

## 7. Reproducción

```bash
# 1. Compilar wrapper propio
gcc -shared -fPIC -o /tmp/wrapper_shm.so iframe_capture/wrapper_swapbuffers_shm.c -ldl -lGL

# 2. Compilar VirtualGL (sin sudo; deps dev extraídas en /tmp/tjpeg si faltan)
cd virtualgl && mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -DTJPEG_INCLUDE_DIR=/tmp/tjpeg/usr/include \
  -DTJPEG_LIBRARY=/tmp/tjpeg/usr/lib/x86_64-linux-gnu/libturbojpeg.so \
  -DOpenCL_LIBRARY=/tmp/tjpeg/usr/lib/x86_64-linux-gnu/libOpenCL.so \
  -DOpenCL_INCLUDE_DIR=/tmp/tjpeg/usr/include \
  -DX11_Xtst_LIB=/tmp/tjpeg/usr/lib/x86_64-linux-gnu/libXtst.so \
  -DCMAKE_CXX_FLAGS="-I/tmp/tjpeg/usr/include"
make -j$(nproc) vglfaker dlfaker gefaker

# 3. Benchmark
python3 docs/bench_capture.py
```
