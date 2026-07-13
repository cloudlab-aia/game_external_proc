# Matriz de carga: FSRCNN (configuración elegida) bajo estrés

Mide la inferencia de FSRCNN x4 (entrada 480×270 → 1080p) en cada dispositivo
bajo los 4 estados de carga, para responder cuánto se degrada cada uno cuando
otro está saturado. Complementa la Fase 1 con la config final (FSRCNN→OpenVINO),
que la matriz original no cubrió. Datos: `load_matrix_fsrcnn.csv`.

- iGPU_OV / CPU_OV → FSRCNN convertido a OpenVINO IR (la config elegida).
- dGPU_OCL → FSRCNN .pb por OpenCL (la dGPU no ejecuta IR de OpenVINO).

## FPS (p50) por dispositivo y carga

| Dispositivo | idle | CPU stress | iGPU stress | dGPU stress |
|---|---|---|---|---|
| **iGPU OpenVINO** | 116 | 100 (−14%) | 50 (−57%) | 80 (−30%) |
| CPU OpenVINO | 162 | 22 (−86%) | 15 | 13 |
| dGPU OpenCL | 11 | 3 | 4 | 3 |

## Lecturas clave

1. **La CPU es la más rápida en reposo (162 FPS) pero se hunde con cualquier
   carga** (−86% con estrés de CPU). Es la opción más frágil: en un juego real
   la CPU está ocupada (lógica del juego, driver), así que rendiría mal.

2. **La iGPU es la más robusta bajo carga cruzada.** Aguanta 80 FPS incluso con
   la dGPU saturada (−30%) y 100 con la CPU saturada (−14%). Nunca baja de los
   ~50 FPS.

3. **Comparando dispositivos BAJO LA MISMA carga** (que es lo que importa en el
   escenario real):
   - Con estrés de CPU: iGPU 100 > CPU 22 > dGPU 3.
   - Con estrés de dGPU (≈ el caso real: la dGPU renderizando el juego):
     iGPU 80 > CPU 13 > dGPU 3.
   En ambos casos **la iGPU gana con claridad**.

4. **La dGPU vía OpenCL es inviable** (≤11 FPS): confirma que el backend OpenCL
   de OpenCV no sirve; la dGPU rápida sería por CUDA, pero esa GPU ya está
   ocupada renderizando.

## Conclusión (justifica la arquitectura)

La elección de la iGPU **no** se justifica por ser la más rápida en reposo (lo
es la CPU). Se justifica porque:
- es la **más estable bajo carga**, y
- en el escenario real la **CPU está ocupada** (juego) y la **dGPU está ocupada**
  (render), mientras la **iGPU está libre**.

Es decir: el reparto dGPU(render) + iGPU(IA) coloca cada tarea donde tiene
recursos disponibles. Los datos lo respaldan.

Nota: la PSNR del CSV está calculada vs bicúbico (no es la métrica de calidad;
para calidad ver Fase 2 / quality_matrix). Aquí solo importan latencia y FPS.
