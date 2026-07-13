# results/: datos medidos (reales)

Todos los datos de este directorio son **medidas reales** obtenidas con los
scripts de `benchmarks/` y `experiments/` sobre el hardware del proyecto
(RTX 5060 + Intel Core Ultra 7 265K), aptas para citar en la memoria. Los
prototipos y simulaciones antiguas viven en `archive/` y no forman parte de
los resultados del trabajo.

| Carpeta | Contenido |
|---|---|
| [`experiments/`](experiments/) | Campaña experimental de la memoria (Exps. 1–11): CSVs por experimento, resúmenes interpretados y gráficas en `plots/`. Incluye la re-ejecución sin VSYNC (`*_novsync.csv`, `expNOVSYNC_RESUMEN.md`) y la latencia por componente (`latency_components.csv`). |
| [`viability_submission/`](viability_submission/) | Estudio de viabilidad de inferencia (Fase 1): matriz de 580 mediciones (6 dispositivos × 6 modelos × cargas), con diccionario de datos e interpretación en `docs/`. |
| [`phase2_quality/`](phase2_quality/) | Comparativa nativo vs híbrido con PSNR/SSIM (Fase 2). |
| [`sample_frames/`](sample_frames/) | Frames de referencia capturados del juego real, incluido el ground truth nativo 4K (`mine_3840x2160.png`) de los experimentos de calidad. |
| [`benchmark_examples/`](benchmark_examples/) | Ejemplos visuales de salida de los primeros benchmarks (FSRCNN x2/x3/x4, CPU vs OpenCL). |

## Correspondencia con los experimentos de la memoria

- **Exp. 1** (FSRCNN por dispositivo): `experiments/exp1_fsrcnn_*.csv`
- **Exps. 2–4** (RealESRGAN, modelo ligero, SuperTuxKart): `viability_submission/`
- **Exp. 5** (cruce dGPU/iGPU bajo carga): `experiments/expB_*` y `experiments/RESUMEN.md`
- **Exp. 6** (nativa vs híbrida vs dedicada): `experiments/exp6_trio_novsync.csv`
- **Exp. 7** (calidad vs ground truth): `experiments/quality_full/` y `experiments/quality_matrix/`
- **Exp. 8** (barrido de resolución y modos): `experiments/fps_resolution_sweep_novsync.csv`
- **Exp. 9** (peso de la IA, híbrida vs dedicada): `experiments/expF_weight_novsync.csv`
- **Exp. 10** (captura sin presentación): `experiments/expH_skip_present.md` y `experiments/expG_resolution_*.csv`
- **Exp. 11** (latencia por componente): `experiments/latency_components.csv`
- Latencia end-to-end captura→pantalla: `experiments/latencia_e2e_fsrcnn_x4.txt`

El protocolo de medida (control de VSYNC, verificación de la resolución
efectiva, condiciones de ventana) está documentado en
`experiments/expNOVSYNC_RESUMEN.md` y en el capítulo de metodología de la
memoria. La comparativa de mecanismos de captura (wrapper vs VirtualGL) está
en `../docs/bench_capture_results.csv` junto a su análisis.
