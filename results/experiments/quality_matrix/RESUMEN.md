# Matriz calidad/latencia: resolución de entrada × factor de escala

Barrido automatizado de TODA resolución de render × cada factor de escala FSRCNN.
Referencia (ground truth): frame nativo real de Minecraft a 1920×1080
(`results/sample_frames/mine_1920x1080.png`). Metodología por combinación:
GT → downsample a la resolución de entrada (render barato) → FSRCNN (iGPU) y
bicúbico → vuelta a la resolución de salida → PSNR/SSIM vs GT.

Datos completos: `quality_resolution_matrix.csv`. Recortes GT|bicúbico|híbrido en
`crops/`. Gráficas en `plots/`.

## Resultado principal — salida fija 1080p (comparables al frame nativo)

| Entrada | Escala | PSNR híbrido | SSIM | vs bicúbico | Latencia IA (iGPU) |
|---|---|---|---|---|---|
| 960×540 | ×2 | **30,04 dB** | 0,876 | +0,18 dB | 63 ms (16 FPS) |
| 640×360 | ×3 | 26,48 dB | 0,751 | +0,15 dB | 33 ms (30 FPS) |
| 480×270 | ×4 | 26,44 dB | 0,706 | +0,31 dB | 22 ms (45 FPS) |

**A misma salida (1080p), rendir 960×540 (×2) da 30,0 dB frente a 26,4 dB de
480×270 (×4): +3,6 dB.** La calidad la marca, sobre todo, **cuántos píxeles
rinde la dGPU**, no el modelo. Esto cuantifica por qué el modo ×4 (480×270) se
ve borroso y el ×2 (960×540) se ve bien.

## El compromiso calidad ↔ rendimiento (estilo DLSS)

| Modo | Render | Escala | Calidad | Coste IA |
|---|---|---|---|---|
| **Calidad** | 960×540 | ×2 | 30,0 dB | 63 ms (16 FPS IA) |
| **Equilibrado** | 640×360 | ×3 | 26,5 dB | 33 ms (30 FPS IA) |
| **Rendimiento** | 480×270 | ×4 | 26,4 dB | 22 ms (45 FPS IA) |

Menos render = más FPS (juego e IA) y menos calidad. Más render = mejor calidad
y menos FPS. Es exactamente el esquema Rendimiento/Equilibrado/Calidad de DLSS,
aquí cuantificado.

## FSRCNN vs bicúbico: la ganancia depende de la escala

- A **×4** FSRCNN aporta lo máximo: **+0,3 a +0,64 dB** sobre bicúbico.
- A **×3**: +0,15 a +0,58 dB.
- A **×2** FSRCNN **pierde** contra bicúbico (−0,03 a −0,24 dB): a ratios bajos,
  el modelo ligero no añade detalle y suaviza de más.

Interpretación: FSRCNN solo compensa cuando hay mucho que reconstruir (escalas
altas). Es coherente con Fase 2: la ganancia del modelo es marginal; el factor
dominante de calidad es la resolución de render.

## Latencia de inferencia (iGPU) vs resolución de entrada

La latencia crece ~lineal con los píxeles de entrada. Umbral 60 FPS (16,6 ms):
- ≤ 480×270 (×4) → 22 ms: por debajo de 60 FPS de inferencia con holgura.
- 960×540 (×2) → 63 ms: ~16 FPS de inferencia; la IA pasa a ser el cuello.

Esto fija el techo práctico: para tiempo real fluido, render ≤ ~480×270 con la
iGPU; por encima, la inferencia domina y conviene bajar resolución o repartir.

## Conclusión

1. **La resolución de render es la palanca de calidad** (+3,6 dB de 480×270 a
   960×540 a misma salida 1080p), no el modelo.
2. **FSRCNN solo aporta a escalas altas** (×3/×4); a ×2 lo bate el bicúbico.
3. **Existe un trade-off calidad↔FPS explícito y medido** que se puede presentar
   como modos (Rendimiento/Equilibrado/Calidad), análogo a DLSS.
