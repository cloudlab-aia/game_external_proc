# Exp F: la ventaja híbrida en la fluidez del juego

Pregunta: cuando la dGPU es el cuello (render por hardware, GPU-bound), ¿la
arquitectura híbrida (IA en la iGPU) mantiene el juego más fluido que hacer la IA
en la propia dGPU (dedicada)?

Montaje: Minecraft + Photon en pantalla real (`:1`, presentación por hardware),
render fijo a 960×540 (x2 → 1080p). Se barre el **peso de la IA** (N inferencias
por frame = modelo N veces más pesado). Se mide, para dedicada (IA dGPU) vs
híbrida (IA iGPU):
- **FPS del juego** (ritmo de render = fluidez/respuesta).
- **FPS entregados** (frames reescalados/s).

## Resultados

| Peso IA | Juego dedicada | **Juego híbrida** | Entreg. dedicada | Entreg. híbrida | GPU ded/hib |
|---|---|---|---|---|---|
| x1 (FSRCNN real) | 27,4 | **34,4** | 27,5 | 26,4 | 95 / 64 |
| x2 | 19,3 | **37,8** | 19,2 | 13,7 | 100 / 63 |
| x3 | 19,3 | **36,1** | 12,9 | 9,2 | 100 / 56 |
| x4 | 19,4 | **36,5** | 9,7 | 7,0 | 100 / 63 |
| x6 | 19,2 | **37,5** | 6,5 | 4,7 | 100 / 62 |
| x8 | 19,1 | **36,2** | 4,9 | 3,5 | 100 / 59 |

Gráficas: `plots/expF_game_fps.png`, `plots/expF_delivered.png`.

## Hallazgos

1. **La híbrida preserva la fluidez del juego (~36 FPS) sea cual sea el peso de
   la IA.** La dGPU queda libre (~60 %) para renderizar. La dedicada satura la
   dGPU (100 %) con render+IA y hunde el juego a ~19 FPS.

2. **Ya con el FSRCNN real (peso x1) la híbrida gana: 34,4 vs 27,4 FPS de juego
   (+26 %).** El margen crece con el peso del modelo (hasta ~2× a peso alto).

3. **Los frames entregados sí los gana la dedicada** (la dGPU es más rápida en
   inferencia), pero mostrando un juego a trompicones (19 FPS por debajo). Dos
   caras del compromiso: fluidez de juego (híbrida) vs ritmo de imagen final
   (dedicada).

## Conclusión

**La arquitectura híbrida permite añadir upscaling por IA SIN sacrificar el
rendimiento del juego**: al ejecutar la IA en la iGPU, la dGPU queda libre para
renderizar (~36 FPS), mientras que ejecutarla en la dGPU la satura y hunde la
fluidez (~19 FPS). Es la justificación a nivel de sistema de la arquitectura, y
se cumple **con el modelo real** (no solo con modelos pesados), en el régimen
correcto: cuando la dGPU es el cuello (render por hardware).

Matiz honesto (importante): esta ventaja aparece con **presentación por
hardware** (GPU-bound). En la pantalla virtual oculta (Xvfb) el cuello es la CPU
y la ventaja no se materializa (ver Exp E y docs/INVESTIGACION_PANTALLA_OCULTA).
