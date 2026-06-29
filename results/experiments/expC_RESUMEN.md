# Exp C — FPS del juego con shaders reales (Photon, Minecraft 1.20.1)

Escena fija, GPU NVIDIA RTX 5060. FPS de render medidos con el contador del
buzón (benchmarks/render_fps.py). Salida común: 1080p.

| Config | Render | IA en | FPS juego | GPU util |
|---|---|---|---|---|
| Nativa | 1920×1080 | — | **9.5** | 97% (saturada) |
| Híbrida | 854×480 | iGPU | **29.0** | 88% |
| Dedicada | 854×480 | dGPU | 30.5 | 88% |
| (render puro 854×480, sin IA) | 854×480 | — | 32.3 | 88% |

## Resultado principal
**La arquitectura híbrida triplica los FPS (3,1×)** a igual resolución de salida
(1080p): renderizar a 854×480 y reconstruir con IA da 29 FPS frente a 9,5 FPS
del render nativo a 1080p. Con shaders pesados (Photon), donde la dGPU se
satura (97% a 1080p), el ahorro de renderizar pocos píxeles es enorme.

## Matiz honesto: colocación de la IA (iGPU vs dGPU)
A baja resolución de render, hacer la IA en la iGPU (29) o en la dGPU (30) da
casi lo mismo. Razón: FSRCNN es tan ligero (~4 ms en dGPU) que cabe en la
holgura de la dGPU aunque esté al 88%. La ventaja de descargar en la iGPU (no
tocar la dGPU) NO se traduce en más FPS de sistema con un modelo tan ligero.

Dónde SÍ importa la iGPU: cuando la dGPU está totalmente saturada y el modelo
es más pesado — ahí la inferencia en dGPU se desploma por debajo de la iGPU
(demostrado en Exp B, gráfica del cruce). Con FSRCNN concreto, el beneficio del
sistema viene del escalado de resolución, no de la colocación de la IA.

## Conclusión para el TFG
1. Beneficio de rendimiento DEMOSTRADO: 3,1× FPS con render bajo + upscaling IA.
2. La arquitectura híbrida (IA en iGPU) iguala a la dedicada SIN ocupar la dGPU,
   dejándola 100% libre para el render — ventaja que escala con modelos más
   pesados (Exp B).
