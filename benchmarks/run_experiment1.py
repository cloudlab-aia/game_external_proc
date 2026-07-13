import cv2
import numpy as np
import time
import onnxruntime
import openvino.runtime as ov

# ==== Configuración ====
RESOLUCIONES_ENTRADA = [
    (128, 72),
    (640, 360),
    (1280, 720),
    (1920, 1080),
    (2560, 1440)
]
RESOLUCION_SALIDA = (3840, 2160)  # 4K

MODELOS_FSRCNN = {
    "FSRCNN_x2": "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x2.pb",
    "FSRCNN_x3": "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x3.pb",
    "FSRCNN_x4": "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x4.pb"
}

MODELO_REALESRGAN = "/home/ogg/Desktop/AIA/game_external_proc/models/RealESRGAN_x4.onnx"

# ==== Funciones ====

def infer_fsrcnn(img, model_path, scale, device="cpu"):
    """
    Inferencia FSRCNN con OpenCV DNN.
    device: "cpu" o "gpu" (iGPU Intel via OpenCL)
    """
    # Forzar OpenCL si se usa GPU
    if device == "gpu":
        cv2.ocl.setUseOpenCL(True)
    else:
        cv2.ocl.setUseOpenCL(False)

    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model_path)
    sr.setModel("fsrcnn", scale)

    start = time.time()
    out = sr.upsample(img)
    end = time.time()
    return out, (end - start) * 1000  # ms

def infer_realesrgan(img, compiled_model):
    """
    Inferencia RealESRGAN con OpenVINO
    """
    input_layer = compiled_model.input(0)
    input_data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    input_data = np.expand_dims(input_data.transpose(2,0,1), axis=0)  # [1,C,H,W]
    
    start = time.time()
    output = compiled_model([input_data])[compiled_model.output(0)]
    end = time.time()

    # Convertir a HWC BGR
    output_img = np.clip(output[0].transpose(1,2,0) * 255, 0, 255).astype(np.uint8)
    output_img = cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR)
    return output_img, (end - start) * 1000

# ==== Main ====
if __name__ == "__main__":
    # Dummy image para pruebas
    for h, w in RESOLUCIONES_ENTRADA:
        dummy_img = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)

        # FSRCNN
        for name, path in MODELOS_FSRCNN.items():
            for device in ["cpu", "gpu"]:
                out, t = infer_fsrcnn(dummy_img, path, scale=int(name[-1]), device=device)
                print(f"Resolución entrada: {w}x{h} | Modelo: {name} | Dispositivo: {device} | Tiempo inferencia: {t:.2f} ms")

        # RealESRGAN con OpenVINO en iGPU
        core = ov.Core()
        try:
            compiled_model = core.compile_model(MODELO_REALESRGAN, device_name="GPU.0")  # iGPU
        except Exception as e:
            print("No se pudo usar iGPU, usando CPU:", e)
            compiled_model = core.compile_model(MODELO_REALESRGAN, device_name="CPU")

        out, t = infer_realesrgan(dummy_img, compiled_model)
        print(f"Resolución entrada: {w}x{h} | Modelo: RealESRGAN_x4 | Dispositivo: {'iGPU' if compiled_model.device_name=='GPU.0' else 'CPU'} | Tiempo inferencia: {t:.2f} ms")
