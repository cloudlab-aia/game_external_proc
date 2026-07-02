# Modos de operación: render + inferencia + calidad (decisión de demo)

Cruce de las dos matrices medidas:
- FPS de render real del juego por resolución (`fps_resolution_sweep.csv`, juego
  en vivo con shaders Photon en la pantalla virtual).
- Calidad (PSNR) y latencia de inferencia iGPU por resolución×escala
  (`quality_resolution_matrix.csv`, offline con frame nativo de referencia).

El **FPS que percibe el usuario = mín(FPS render, FPS inferencia)**: el pipeline
no puede ir más rápido que su etapa más lenta.

## Los tres modos (salida fija 1080p)

| Modo | Render | Escala | FPS render | FPS IA (iGPU) | **FPS visible** | Cuello | PSNR |
|---|---|---|---|---|---|---|---|
| **Rendimiento** | 480×270 | ×4 | 35 | 45 | **~35** | render/Xvfb | 26,4 dB |
| **Equilibrado** | 640×360 | ×3 | 35 | 30 | **~30** | inferencia | 26,5 dB |
| **Calidad** | 960×540 | ×2 | 28 | 16 | **~16** | inferencia | 30,0 dB |

## Lecturas

1. **El modo calidad lo limita la iGPU, no el render.** A 960×540 la inferencia
   FSRCNN tarda ~63 ms (16 FPS); el render da 28 FPS. → no se puede tener
   "nítido y fluido" a la vez en la iGPU. Es el límite real del hardware de
   inferencia, no de la captura ni del render.

2. **A baja resolución el cuello es CPU/Xvfb (~35 FPS), no la dGPU.** El FPS de
   render es plano (35) de 426×240 a 640×360 → la dGPU tiene margen de sobra;
   la pantalla virtual (Xvfb) + la CPU de Minecraft ponen el techo.

3. **Compromiso explícito calidad↔fluidez:**
   - Demo fluido (35 FPS) → 480×270 ×4, pero se ve borroso (26 dB).
   - Demo nítido (30 dB) → 960×540 ×2, pero a 16 FPS (entrecortado).
   - Punto medio razonable: **640×360 ×3 → ~30 FPS** (la calidad apenas sube
     sobre ×4; el valor está en la fluidez).

## Recomendación para la presentación

Para un demo **jugable y fluido**: **640×360 ×3** (≈30 FPS visibles, una ventana,
con shaders). Si el objetivo es enseñar **calidad**, mostrar una captura estática
en modo 960×540 ×2 (30 dB) junto al render bajo, sin exigir tiempo real.

El mensaje de tesis: la arquitectura híbrida funciona y es jugable; el techo de
calidad en tiempo real lo fija la **capacidad de inferencia de la iGPU**, no la
captura (−7%) ni el render (dGPU con margen). Resultado cuantificado, no opinión.
