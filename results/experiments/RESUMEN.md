# Experimentos — Arquitectura híbrida vs dedicada (FSRCNN)

Inferencia de FSRCNN (Y, 480×270→1080p salvo barrido) en las tres unidades:
dGPU (NVIDIA RTX 5060, ONNX Runtime CUDA), iGPU (Intel, OpenVINO), CPU (OpenVINO).

## Exp A — Inferencia sin carga (barrido)
A reposo, la dGPU es la más rápida en TODA combinación de resolución y escala;
la iGPU es la más lenta. (`expA_inference_sweep.csv`, `plots/sweep_x*.png`)

| Escala x4, 480×270 | dGPU | CPU | iGPU |
|---|---|---|---|
| FPS inferencia | 243 | 161 | 110 |

## Exp B — Cruce al saturar la dGPU (figura estrella)
Conforme se carga la dGPU, su FPS de inferencia se desploma; la iGPU se mantiene
plana. **Al saturar la dGPU, la iGPU la supera.** (`expB_gradient.csv`,
`plots/crossover.png`)

| Carga dGPU | dGPU FPS | iGPU FPS |
|---|---|---|
| 0% | 241 | 95 |
| 88% | 198 | 106 |
| 98% | 155 | 99 |
| (más) | 124 | 90 |
| (más) | 104 | 95 |
| (máx) | 90 | 91 ← CRUCE |

## Estabilidad bajo carga (matriz)
La iGPU apenas se degrada ante cualquier carga (CPU/iGPU/dGPU). La CPU se hunde
bajo carga de CPU (−85%). (`expB_crossover.csv`, `plots/load_matrix.png`)

## Conclusión
- En inferencia AISLADA, la dGPU gana siempre: la iGPU no es "más rápida".
- PERO al saturar la dGPU (≈ renderizando un juego), su inferencia cae por
  debajo de la iGPU → existe un régimen donde la híbrida (IA en iGPU) es mejor.
- La iGPU aporta ESTABILIDAD y, sobre todo, está LIBRE mientras la dGPU renderiza.
- Pendiente Exp C: medir FPS del juego con shaders (nativa vs dedicada vs híbrida),
  la demostración a nivel de sistema.
