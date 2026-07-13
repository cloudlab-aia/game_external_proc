# archive/ — Material apartado (NO usar como fuente de medidas)

Cosas que formaron parte de la exploración pero que no son la versión final
del TFG. Se conservan como evidencia del proceso, no como resultados.

## simulation_analysis/ 

Scripts que **SIMULAN** rendimiento (generan números a partir de modelos
analíticos, no de mediciones):

- `realesrgan_hybrid_realistic_analysis.py` — "simula de forma REALISTA" el
 rendimiento Real-ESRGAN en la arquitectura híbrida.
- `comprehensive_glxgears_realesrgan_analysis.py` — análisis exhaustivo con
 componentes simulados.

**Nunca presentar la salida de estos scripts como medidas reales en la
memoria.** Para medidas reales: `../benchmarks/` y `../results/`.

## analysis_runs/

Salidas con timestamp de ejecuciones antiguas (gráficas, JSON, informes).
Mezcla de ejecuciones reales y simuladas — comprobar qué script las generó
antes de usar cualquiera.

## early_experiments/

Prototipos tempranos previos al diseño actual:

- `tst/` — primeros tests de proceso dual GPU en C++ (capture/process).
- `multi_gpu_test.cpp` — test inicial de contextos en 2 GPUs.
- `reader_gpu1.py`, `web_stream_gpu2.py` — lectores del formato shm v1 (sin header).
- `reloj_analogico.py` — app de prueba (reloj analógico) para generar frames.
- `run_glxgears.sh` — lanzador suelto de glxgears interceptado.
- `test_espcn.py`, `test_model.py` — pruebas puntuales de carga de modelos.
