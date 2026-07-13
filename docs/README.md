# docs/: documentación del proyecto

| Archivo | Contenido |
|---|---|
| `JUSTIFICACION_WRAPPER_VS_VIRTUALGL.md` | **Decisión clave del TFG:** comparativa medida entre el interceptor propio y VirtualGL modificado (mismo bloque de captura). Resultado: wrapper 2,7–3,2× menos overhead. Incluye metodología, amenazas a la validez y reproducción. |
| `bench_capture.py` | Script del benchmark anterior (baseline / wrapper / VirtualGL × 3 resoluciones). |
| `bench_capture_results.csv` | Datos crudos de esa comparativa (2026-06-11, RTX 5060). |
| `virtualgl_hybrid_capture.patch` | Modificaciones completas realizadas sobre VirtualGL 3.x para la evaluación anterior: hook `hybridCaptureToShm()` en `server/faker-glx.cpp` (mismo formato de shm que el wrapper), soporte OpenCL en el build e instrucciones. Se aplica sobre el código fuente oficial de VirtualGL con `git apply`. La alternativa se evaluó y se descartó, por lo que el fork completo no se mantiene en este repositorio. |
| `INVESTIGACION_PANTALLA_OCULTA.md` | Estudio de las alternativas de pantalla oculta (Xvfb, VirtualGL, PRIME, DRM) que llevó a la solución final de captura sin presentación. |
