# capture/: interceptor de frames OpenGL

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

## Compatibilidad con juegos reales (Minecraft)

El interceptor cubre las tres rutas por las que una app puede llegar a
`glXSwapBuffers`:

1. Enlace dinámico normal (PLT), glxgears y apps clásicas.
2. `dlsym()` sobre libGL cargada con `dlopen()`, GLFW/LWJGL3 (Minecraft ≥ 1.13).
3. `glXGetProcAddress[ARB]()`, resolución de extensiones.

Variables de entorno:

- `FRAME_CAPTURE_EXE=<subcadena>`, limita la captura al proceso cuyo nombre
  contenga la subcadena (p. ej. `java` = solo la JVM del juego). Necesario al
  inyectar a través de un launcher: si dos procesos escriben a la vez en la
  shm con tamaños distintos, el `ftruncate` de uno invalida el mapeo del otro
  (SIGBUS).
- El tamaño del frame se toma de `glXQueryDrawable` (tamaño de ventana), no
  del viewport: juegos como Minecraft cambian `glViewport` varias veces por
  frame.

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
