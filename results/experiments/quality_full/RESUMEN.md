# Matriz completa entrada × salida (720p → 4K)

Barrido exhaustivo: **cada resolución de entrada 16:9 típica × cada salida
estándar de display (720p, 1080p, 1440p, 4K)**, con el factor de escala efectivo
= salida/entrada (todos los que surgen, de ×1,1 a ×15). 44 combinaciones.

- **Referencia (GT)**: frame nativo REAL de Minecraft a 3840×2160
  (`results/sample_frames/mine_3840x2160.png`), capturado renderizando el juego a
  4K en la dGPU. Cada salida = master remuestreado (INTER_AREA) a esa resolución.
- **Render bajo (LR)**: GT remuestreado por bicúbico a la resolución de entrada
  (protocolo SR estándar; FSRCNN se entrena/evalúa con degradación bicúbica).
- **Híbrido** = FSRCNN al factor entero más cercano (×2/×3/×4) + resize bicúbico
  al tamaño de salida exacto (idéntico al pipeline real). **Bicúbico** = upscale
  directo. Métricas PSNR/SSIM vs GT + latencia de inferencia (iGPU).

Datos: `quality_full_matrix.csv`. Gráficas: `plots/`.

## Hallazgos

### 1. La resolución de render es la palanca de calidad (no el modelo)
PSNR sube con la resolución de entrada y baja con la de salida (más upscaling =
más difícil). Para salida 1080p:

| Entrada | Escala | PSNR híbrido | Latencia IA |
|---|---|---|---|
| 256×144 | ×7,5 | 26,0 dB | 3,6 ms (muy rápido) |
| 480×270 | ×4 | 29,3 dB | 14 ms (70 FPS) |
| 640×360 | ×3 | 31,0 dB | 21 ms (48 FPS) |
| 960×540 | ×2 | 35,0 dB | 39 ms (25 FPS) |
| 1280×720 | ×1,5 | 37,2 dB | 73 ms (14 FPS) |

De 256×144 a 1280×720 (misma salida 1080p): **+11 dB**. El salto de calidad lo
da rendir más píxeles, no el reescalador.

### 2. FSRCNN aporta poco y es marginal en toda la rejilla
Ganancia híbrido vs bicúbico: **de +0,0 a +0,9 dB**. Máxima en el factor ×2
exacto (p.ej. 640×360→720p: +0,69 dB; 1920×1080→4K: +0,39 dB). En factores altos
(×4) la ganancia es ~+0,1 dB. Coherente con Fase 2: el modelo ligero apenas mejora
el bicúbico; su valor está en el coste, no en la calidad.

### 3. La latencia depende de la ENTRADA, no de la salida
El coste de FSRCNN ∝ píxeles de entrada × factor²; el resize final es barato. Por
eso 480×270→4K cuesta solo 14 ms aunque la salida sea enorme, mientras
1920×1080→4K cuesta 163 ms. → **para tiempo real, lo que importa es bajar la
resolución de render, no la de display.**

### 4. Viabilidad en tiempo real por salida (umbral ~30 FPS = 33 ms)
- **720p / 1080p**: viables hasta entradas medias (≤960×540 ≈ 25-70 FPS de IA).
- **1440p**: viable solo desde entradas bajas (≤640×360); por encima, IA > 40 ms.
- **4K**: la IA es rápida desde entradas bajas (≤768×432, <37 ms) pero la calidad
  cae a ~28-30 dB; con entradas altas (1080p→4K) la IA sube a 163 ms (6 FPS).
  **4K híbrido en tiempo real obliga a calidad baja.**

## Conclusión

Rejilla entrada×salida completa medida (720p→4K, todos los factores). Tres ejes
claros para elegir punto de operación: **resolución de render (calidad),
resolución de display (objetivo), latencia (tiempo real)**. El modelo FSRCNN es
marginal; el sistema se gobierna por la resolución de render. Para tiempo real
fluido a 1080p el punto dulce es render 480×270–640×360 (≈30-70 FPS de IA,
29-31 dB); para máxima calidad jugable, 960×540 (35 dB, ~25 FPS).
