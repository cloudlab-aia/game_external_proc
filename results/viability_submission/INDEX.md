# Thesis Submission Package

Completo benchmark de viabilidad para upscaling AI en tiempo real. Contenido:

## 📊 Visualizations (`plots/`)
**Mostrar primero al tutor:**

1. **device_ranking_idle.png** — Ranking FPS por dispositivo (idle)
   - Muestra jerarquía: dGPU_OCL > iGPU > CPU
   
2. **latency_vs_resolution.png** — Latencia vs resolución entrada (4 load states)
   - Muestra escalado de dispositivos y degradación bajo carga
   
3. **fps_comparison.png** — FPS por modelo (comparativa agrupada)
   - Muestra diferencias entre FSRCNN_x2/x3/x4 y OpenVINO model
   
4. **interference_heatmap.png** — Impacto de stressers (2D devices × load)
   - Muestra cuáles dispositivos son inmunes a CPU stress
   
5. **model_quality_proxy.png** — Scatter latency vs scale factor
   - Muestra tradeoff calidad/velocidad

## 🖼️ Representative Comparisons (`comparisons/`)
**14 imágenes estratégicas:**

- **CPU_OCV** (2x): Baseline, con/sin CPU stress → Referencia lenta
- **CPU_OV** (2x): OpenVINO CPU, muestra mejora respecto a OpenCV
- **iGPU_OCL** (2x): GPU integrada, 2 resoluciones
- **iGPU_OV** (2x): GPU integrada + OpenVINO, comparar vs OCL
- **dGPU_OCL** (6x): 
  - 3 resoluciones (320×180, 640×360, 1280×720) bajo idle
  - 2 interference tests (CPU stress + memory) en 640×360
  - Mejor rendimiento global

Cada PNG muestra: Original | Bicubic | AI upscale (con PSNR + FPS)

## 📋 Documentation (`docs/`)

1. **RESULTS_SUMMARY.md**
   - Combos viables (≥30 fps)
   - Ranking por dispositivo/modelo
   - Degradación bajo stressers
   
2. **DATA_DICT.md**
   - Definición columnas CSV
   - Umbrales viabilidad
   - Metodología medición
   
3. **INTERPRETATION.md**
   - Por qué cada dispositivo se comporta así
   - Limitaciones arquitectura (ONNX format, OpenCL vs CUDA, etc.)
   - Recomendaciones para fase 2

## 📊 Raw Data (`data/`)

- **frame_injection_results.csv** (99 rows)
  - Latencies, FPS, PSNR para cada combo device/model/resolution/interference
  
- **summary_by_device.csv**
  - Agregación por dispositivo

## 🎯 Presentation Strategy

1. **Primera impresión:** Mostrar `device_ranking_idle.png` → "dGPU 986 FPS viable"
2. **Escalado:** `latency_vs_resolution.png` → comportamiento con resoluciones altas
3. **Interferencias:** `interference_heatmap.png` → dGPU inmune, CPU OV vulnerable
4. **Visuals:** Seleccionar 3-4 comparaciones más impactantes (ej: dGPU a 1280×720)
5. **Profundidad:** Referencia RESULTS_SUMMARY.md + INTERPRETATION.md

---

**Hardware usado:** RTX 5060 (dGPU), Intel iGPU, CPU (Intel Core)  
**Modelos:** FSRCNN_x2/x3/x4, RealESRGAN, OpenVINO single-image-super-resolution-1032  
**Resoluciones:** 320×180, 640×360, 1280×720  
**Stressers:** idle, CPU (stress --cpu 8), memory (2GB alloc)  
**Total mediciones:** 99 combos exitosos (7.9% failures en OpenVINO reshape)
