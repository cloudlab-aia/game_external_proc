# processing/ — Superresolución IA sobre los frames capturados

Lectores de `/dev/shm/framebuffer_shared` que aplican superresolución en la
**iGPU Intel** (la dGPU NVIDIA queda libre para el render del juego) y
muestran o transmiten el resultado.

## Archivos

| Archivo | Backend | Qué hace |
|---|---|---|
| `upscale_display.py` | **OpenVINO (principal)** | Pipeline de referencia del TFG. Modelo `single-image-super-resolution-1032` en iGPU (`device=GPU`), ventana cv2 con latencia medida (~10–15 ms). |
| `upscale_openvino.py` | OpenVINO | Variante con Real-ESRGAN ONNX. |
| `upscale_onnx.py` | ONNX Runtime | Variante con onnxruntime como motor de inferencia. |
| `upscale_fsrcnn.py` | OpenCV dnn_superres | Variante FSRCNN (modelos .pb), OpenCL sobre iGPU. |
| `run_realesgran.py` | PyTorch | Real-ESRGAN nativo (.pth). Pesado; usado para comparativas de calidad, no para tiempo real. |
| `run_realesrgan_onnx.py` | ONNX Runtime | Real-ESRGAN exportado a ONNX. |
| `realtime_display_igpu.py` | OpenCV | Visor en tiempo real con monitor de FPS, sin superresolución (diagnóstico). |
| `web_stream.py` | Flask | Streaming HTTP de los frames (`http://localhost:5000/video_feed`). |

## Selección de GPU

Forzado de iGPU Intel mediante entorno (los lanzadores de `pipeline/` ya lo hacen):

```bash
CUDA_VISIBLE_DEVICES=""        # ocultar NVIDIA a OpenCV/OpenVINO
OPENCV_OCL_DEVICE="1:GPU:0"    # plataforma OpenCL 1 = Intel
```

Los modelos se cargan desde `../models/` (rutas configuradas al inicio de
cada script).
