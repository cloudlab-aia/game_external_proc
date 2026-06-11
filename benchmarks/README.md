# benchmarks/ — Medición de rendimiento (datos REALES)

Scripts de experimentación que producen las medidas usadas en la memoria.
Todo lo de esta carpeta **mide**, no simula. (Los scripts de simulación
están en `../archive/simulation_analysis/` y NO deben citarse como medidas.)

## Experimento principal

| Archivo | Qué hace |
|---|---|
| `run_experiment1.sh` | Barrido de resoluciones (128×72 → 2560×1440): lanza glxgears interceptado y benchmarkea modelos en cada resolución. |
| `run_experiment1.py` / `run_experiment1_glxgears.py` / `run_experiment1_realtime_igpu.py` | Variantes del experimento 1 (offline / con glxgears en vivo / con visor tiempo real). |
| `benchmark_models.py` | Núcleo de benchmarking: lee frames reales de la shm y mide latencia/FPS de cada modelo de superresolución (FSRCNN, ESPCN, ONNX). Salida CSV. |
| `benchmark_models_shm.py` | Variante acoplada al formato shm con header. |
| `run_bench_orchestrator.py` / `run_benchmark_with_glxgears.py` | Orquestadores: levantan app interceptada + benchmark automáticamente. |

## Real-ESRGAN y monitorización

| Archivo | Qué hace |
|---|---|
| `realesrgan_igpu_real_analysis.py` | FPS reales con Real-ESRGAN ejecutándose en iGPU (nativo vs con modelo). |
| `bench_realesgran.py` | Benchmark Real-ESRGAN por resoluciones. |
| `fps_monitor.py` | Lee el contador `seq` del header shm y reporta FPS de captura en vivo. |
| `analisis_benchmark.py` | Análisis/gráficas de los CSV de resultados. |
| `real_data_analysis_suite.py` | Suite de informes a partir de los CSV de datos reales existentes. |

## Resultados

Los CSV y ejemplos generados van a `../results/`. La comparativa
wrapper vs VirtualGL (con su propio script) está en `../docs/`.
