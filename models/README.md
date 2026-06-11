# models/ — Modelos de superresolución

| Archivo | Formato | Usado por |
|---|---|---|
| `single-image-super-resolution-1032.xml/.bin` | OpenVINO IR | **`processing/upscale_display.py` (pipeline principal).** Modelo de Intel Open Model Zoo, x3, dos entradas (LR 480×270 + HR original). |
| `FSRCNN_x2.pb / _x3.pb / _x4.pb` | TensorFlow | Fuente de los IR de abajo; `processing/upscale_fsrcnn.py`. |
| `fsrcnn_x4_ov.xml/.bin`, `fsrcnn_x2_ov.xml/.bin` | OpenVINO IR | **Vía jugable** (`processing/upscale_fsrcnn_ov.py`). FSRCNN convertido con entrada fija (480×270 / 960×540). ~13 ms/frame en iGPU vs 95–350 ms del backend OpenCL de OpenCV (roto en esta iGPU). |
| `RealESRGAN_x4.onnx` | ONNX | `processing/upscale_openvino.py`, `run_realesrgan_onnx.py`. |
| `RealESRGAN_x4plus.pth` | PyTorch | `processing/run_realesgran.py` (comparativa de calidad). |
| `realesr-animevideov3.pth` | PyTorch | Variante ligera de Real-ESRGAN para vídeo. |
| `super-resolution-10.onnx` | ONNX | Modelo x2 (224×224) de pruebas iniciales. |
| `Real-ESRGAN/` | submódulo git | Código fuente de Real-ESRGAN (necesario para los .pth). |

## Utilidades

- `download_model.py` — descarga de modelos.
- `convert_realesrgan.py` — conversión .pth → ONNX.
- `setup_model.py` — preparación/verificación de modelos.

Las rutas a estos modelos están definidas como constantes al inicio de cada
script de `processing/` y `benchmarks/`.
