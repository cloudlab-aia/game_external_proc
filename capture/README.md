# capture/ — Interceptor de frames OpenGL

Biblioteca `LD_PRELOAD` que intercepta `glXSwapBuffers` de cualquier
aplicación OpenGL y copia cada frame a memoria compartida POSIX
(`/dev/shm/framebuffer_shared`).

## Archivos

| Archivo | Qué es |
|---|---|
| `wrapper_swapbuffers_shm.c` | **Interceptor actual.** Header de 16 bytes (`uint32`: width, height, seq, ready) + frame RGBA con flip vertical. Resolución dinámica, mapeo shm cacheado, detección de frames negros. |
| `build.sh` | Compila el interceptor. Genera `wrapper_swapbuffers_shm.so` y el alias `libswapcapture.so` (ambos nombres usados por scripts). |
| `legacy/wrapper_swapbuffers_shm_v1.c` | Versión anterior: 1920×1080 fijo, **sin header**, reabría la shm en cada frame. Útil en la memoria como evolución del diseño. |
| `legacy/wrapper_swapbuffers_v0.c` | Primer prototipo de interceptación. |
| `legacy/frame_capture_variant.c` | Variante experimental intermedia. |

## Uso

```bash
./build.sh
LD_PRELOAD=$PWD/wrapper_swapbuffers_shm.so glxgears -geometry 1280x720
# En otra terminal: cualquier lector de processing/ o benchmarks/
```

## Formato de la memoria compartida (versión actual)

```
offset 0:  uint32 width
offset 4:  uint32 height
offset 8:  uint32 seq      (contador de frames, monotónico)
offset 12: uint32 ready    (0 = escribiendo, 1 = frame completo)
offset 16: píxeles RGBA, ya volteados verticalmente (origen arriba-izquierda)
```

Los lectores antiguos del formato v1 (sin header) NO son compatibles con
este formato y viceversa.
