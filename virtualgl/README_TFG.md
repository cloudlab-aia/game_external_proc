# virtualgl/ — Alternativa evaluada (no es la vía adoptada)

Fork del código fuente de VirtualGL usado para evaluar experimentalmente la
captura vía VirtualGL frente al interceptor propio de `../capture/`.
**Conclusión: se adoptó el interceptor propio** — ver
`../docs/JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md` (wrapper 2,7–3,2× menos
overhead de captura).

## Modificaciones sobre VirtualGL original

- `server/faker-glx.cpp` — función `hybridCaptureToShm()` añadida al hook de
  `glXSwapBuffers`: copia cada frame a `/dev/shm/framebuffer_shared` con el
  mismo formato (header 16 bytes + RGBA) que el interceptor propio, de modo
  que los lectores Python funcionan igual con ambas vías.
- `server/faker-glx.cpp.backup` — copia del original antes del hook.
- `server/CMakeLists.txt` — eliminado un `find_package(CUDA REQUIRED)`
  erróneo de una iteración anterior.

## Compilar (sin instalar en el sistema)

```bash
cd build  # crear si no existe
cmake .. -DCMAKE_BUILD_TYPE=Release  # ver docs/JUSTIFICACION_*.md si faltan deps
make -j$(nproc) vglfaker dlfaker gefaker
```

Nota: el target `vglfaker-nodl` no enlaza (el hook usa funciones GL directas
y esa variante no enlaza libGL); no es necesario para la comparativa.

## Usar

```bash
DISPLAY=:1 VGL_DISPLAY=:1 \
  LD_PRELOAD=$PWD/build/lib/libdlfaker.so:$PWD/build/lib/libvglfaker.so \
  glxgears
```
