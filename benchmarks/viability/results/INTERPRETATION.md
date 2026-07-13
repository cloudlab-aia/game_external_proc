# Interpretación técnica y recomendaciones

## Por qué domina dGPU_CUDA

La eficiencia del backend CUDA viene de tres factores:

1. **Pipeline de acceso directo a memoria (DMA):** CUDA evita la
   indirección de la cola de comandos de OpenCL. Encolar un kernel tiene
   una latencia muy inferior a la de `clEnqueueNDRangeKernel`.

2. **Ejecución de operadores fusionados:** en la RTX 5060, CUDA usa los
   tensor cores (modo TF32) para las operaciones matriciales. Las
   implementaciones OpenCL caen a operaciones escalares en la ALU y pierden
   entre 4 y 8 veces de rendimiento por vatio.

3. **Sin jitter de sincronización CPU-GPU:** el modelo asíncrono de CUDA
   evita el sondeo desde el host que se aprecia en dGPU_OCL. A 224×224,
   dGPU_CUDA consigue p50 = 1,01 ms frente a los más de 39 ms de dGPU_OCL a
   la misma resolución (39 veces más lento). La diferencia se reduce a
   resoluciones grandes, donde el cómputo domina sobre la sincronización.

**Datos:** dGPU_CUDA incluso *mejora* su latencia bajo carga de CPU (-8,2 %)
y bajo carga de iGPU (-4,2 %), señal de su independencia de la contención
del host. dGPU_OCL se degrada un +2,5 % bajo carga de CPU y un +23,9 % bajo
carga de dGPU: es sensible a la contención global del sistema.

---

## Por qué sobrevive CPU_OCV

Despachar en la CPU no tiene sobrecoste de GPU. Para entradas pequeñas
(128×72, 256×144), el coste de mover los datos a memoria de GPU, insertar
en la cola de comandos y lanzar el kernel supera lo que le cuesta a la CPU
hacer el upscaling FSRCNN en el propio proceso.

A 128×72, FSRCNN_x2 en CPU_OCV corre a **660 fps** (1,5 ms de p50). Solo
mover los datos a iGPU_OCL cuesta unos 10 ms, así que la CPU es la elección
lógica para entradas por debajo de 256×144.

**Degradación bajo carga:** CPU_OCV pierde un +10,6 % de latencia bajo carga
de CPU (esperable, los núcleos compiten) pero apenas nota las cargas de
iGPU/dGPU (-0,4 % y +8,0 %): es casi inmune a la contención de GPU.

**Por qué falla a 480×270:** el coste de FSRCNN crece de forma cuadrática
con la resolución de entrada. A 480×270 la CPU necesita 60 ms en reposo,
frente a un presupuesto de 33 ms por frame para 30 fps. Ese es el punto de
inflexión donde la GPU se vuelve necesaria.

---

## Consistencia de la iGPU y ratios p90/p50

| Dispositivo | Ratio en reposo | Ratio bajo carga | Tipo de varianza |
|-------------|-----------------|------------------|------------------|
| CPU_OCV | 1,23 | 1,30 | Ruido del sistema (jitter del SO) |
| iGPU_OCL | 1,04 | 1,15 | Contención de memoria, sin desalojo |
| dGPU_OCL | 1,06 | 2,35 | Acumulación en la cola de la GPU, varianza alta |
| dGPU_CUDA | 1,14 | 1,30 | Loteado en tensor cores |

**iGPU_OCL en reposo: p90/p50 = 1,04**, un valor muy ajustado. El despacho
de comandos OpenCL es determinista sin contención. Eso sí, la latencia
absoluta (10-11 ms incluso a 128×72) está dominada por el coste fijo, no
por el cómputo.

**dGPU_OCL bajo carga de dGPU: p90/p50 = 2,35**, la peor variabilidad. Las
colas de comandos de la GPU se reordenan y priorizan, y los kernels
concurrentes provocan conflictos de bancos de memoria.

---

## Límites de resolución por dispositivo

### Límites prácticos para la integración con un juego (30 fps)

| Dispositivo | Límite a 60 fps | Límite a 30 fps | Motivo |
|-------------|-----------------|-----------------|--------|
| **CPU_OCV** | 256×144 | 320×180 | Escalado cuadrático de FSRCNN |
| **iGPU_OCL** | 128×72 | 128×72 (falla a 256) | 10 ms fijos de despacho + 3 ms de cómputo |
| **dGPU_OCL** | 128×72 | 256×144 | 25 ms de latencia de lanzamiento + 3 ms de cómputo |
| **CPU_OV** | 224×224* | 224×224* | ONNX requiere 224×224 fijo |
| **iGPU_OV** | 224×224* | 224×224* | Misma restricción de ONNX |
| **dGPU_CUDA** | 224×224* | 224×224* | Misma restricción de ONNX |

*Los modelos ONNX (RealESRGAN, super-resolution-10) no admiten entradas de
tamaño variable: la entrada se redimensiona internamente a 224×224 antes de
la inferencia. Los FSRCNN en .pb admiten resoluciones arbitrarias.

### Análisis por resolución

- **128×72 (mínima):** todos los dispositivos viables a ≥60 fps
  (CPU_OCV: 660 fps).
- **320×180 (upscale a 1280×720):** CPU_OCV marginal (55,9 fps); hace falta
  GPU para tiempo real estable.
- **480×270 (upscale a 1920×1080):** CPU_OCV falla (16,6 fps) y dGPU_OCL
  también (11 fps). Solo dGPU_CUDA sería viable a esta resolución.
- **1280×720 (entrada para 4K):** solo dGPU_CUDA en principio; todas las
  variantes de CPU y OpenCL caen por debajo de 2 fps.

---

## Recomendaciones para el trabajo

Las conclusiones que esta fase aporta al diseño de la arquitectura:

1. **dGPU_CUDA domina** porque CUDA elimina el sobrecoste de despacho de
   OpenCL (dos órdenes de magnitud en la latencia de lanzamiento).
2. **CPU_OCV sigue teniendo sentido** para entradas pequeñas (<256×144),
   donde el coste de despachar a la GPU supera al del cómputo.
3. **La consistencia de la iGPU** (p90/p50 ≈ 1,04) demuestra que OpenCL es
   estable aunque lento: su sobrecoste es fijo, no variable.
4. **La varianza de dGPU_OCL** (p90/p50 ≈ 2,35 bajo carga) muestra que la
   planificación de la GPU es un cuello de botella crítico en OpenCL.
5. **El framework importa:** el mismo modelo puede ir sobrado en un backend
   e inviable en otro; la elección de OpenVINO para la iGPU en las fases
   siguientes sale de aquí.

| Requisito | Dispositivo | Resolución | FPS | Motivo |
|-----------|-------------|------------|-----|--------|
| Máximo rendimiento | dGPU_CUDA | 224×224 | 986 | Tensor cores + ejecución directa CUDA |
| Eficiencia energética | iGPU_OV | 224×224 | 336 | Bajo consumo y consistente |
| Solo CPU | CPU_OV | 224×224 | 88 | Portable, sin GPU |
| Entradas diminutas | CPU_OCV | 128×72 | 660 | Despacho sin coste, latencia mínima |
