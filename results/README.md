# results/ — Datos medidos (reales)

Resultados experimentales obtenidos con los scripts de `../benchmarks/`.
Todo lo de esta carpeta proviene de **mediciones reales** en el hardware del
proyecto (RTX 5060 + Intel iGPU), aptas para citar en la memoria.

| Archivo | Origen | Contenido |
|---|---|---|
| `results_experiment1.csv` | `benchmarks/run_experiment1.sh` | Latencia/FPS por modelo y resolución (barrido 128×72 → 2560×1440). |
| `benchmark_results.csv` | `benchmarks/benchmark_models.py` | Medidas de modelos de superresolución sobre frames reales de la shm. |
| `benchmark_examples/` | `benchmarks/benchmark_models.py` | Capturas PNG de salida de cada modelo (FSRCNN x2/x3/x4, CPU vs OpenCL) para comparación visual de calidad. |

La comparativa de mecanismos de captura (wrapper vs VirtualGL) está en
`../docs/bench_capture_results.csv` junto a su análisis.

Ejecuciones antiguas con timestamp (incluidas las de scripts de simulación)
están en `../archive/analysis_runs/` — revisar su origen antes de usar
cualquiera en la memoria.
