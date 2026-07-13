# phase2/: comparativa de arquitecturas (nativo vs híbrido)

Fase 2 del TFG (acordada con el tutor): comparar, frame a frame, la imagen
producida por el pipeline híbrido (render bajo en dGPU + upscaling IA en
iGPU) frente al render nativo y al baseline bicúbico, con métricas de calidad
(PSNR/SSIM).

Importado desde el repo TFG_CODE y adaptado a este repositorio.

## Scripts

| Archivo | Qué hace |
|---|---|
| `hybrid_pipeline.py` | Lee frames de `/dev/shm/framebuffer_shared` (header `IIII`), aplica FSRCNN IR sobre el canal Y con OpenVINO (iGPU/CPU/dGPU) + croma bicúbico, y guarda `hybrid_frames/`, `lowres_frames/`, `bicubic_frames/`. Reporta latencia/FPS. |
| `compare_frames.py` | PSNR/SSIM frame a frame: híbrido vs bicúbico, y opcionalmente vs un render nativo de referencia. Salida CSV + imágenes diferencia. |
| `simulate_game.py` | Alimenta la shm con imágenes/vídeo a un FPS dado, **sin necesidad de juego real** (para test del pipeline). Requiere `posix_ipc`. |
| `run_hybrid_test.sh` | Orquesta una prueba completa. |

## Uso con juego real (Minecraft)

```bash
# Terminal 1: capturar el juego (ver pipeline/run_minecraft_*.sh)
# Terminal 2: procesar y guardar frames
python3 phase2/hybrid_pipeline.py --model models/openvino_ir/FSRCNN_x4.xml \
    --scale 4 --max_frames 300 --out_dir phase2/results --save_lowres
# Terminal 3: métricas
python3 phase2/compare_frames.py --hybrid phase2/results/hybrid_frames \
    --bicubic phase2/results/bicubic_frames --out_csv phase2/results/metrics.csv
```

## Uso sin juego (test con muestras)

```bash
python3 phase2/simulate_game.py --source results/sample_frames/mine_480x270.png --fps 60 --loop &
python3 phase2/hybrid_pipeline.py --model models/openvino_ir/FSRCNN_x4.xml --scale 4 --max_frames 30 --out_dir phase2/results --save_lowres
```

Nota: los modelos `models/openvino_ir/FSRCNN_x{2,3,4}.xml` son de **entrada
flexible** (cualquier resolución). La salida del IR es NCHW `(1,1,H,W)`.
`phase2/results/` no se versiona (frames generados por ejecución).
