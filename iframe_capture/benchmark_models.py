import cv2
import time
import numpy as np
import os
from cv2 import dnn_superres

# Configuración general
INPUT_SIZES = [
    (128, 72),
    (640, 360),
    (1280, 720),
    (1920, 1080),
    (2560, 1440)
]
OUTPUT_SIZE = (3840, 2160)  # 4K
MODELS = [("fsrcnn", [2, 3, 4])]
DEVICES = ["cpu", "opencl"]
MODELS_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models"
SHM_PATH = "/dev/shm/framebuffer_shared"  # Imagen escrita por libswapcapture.so


def load_model(sr, model_name, scale):
    model_path = os.path.join(MODELS_PATH, f"{model_name.upper()}_x{scale}.pb")
    sr.readModel(model_path)
    sr.setModel(model_name.lower(), scale)


def read_frame(width, height):
    try:
        with open(SHM_PATH, 'rb') as f:
            data = f.read(width * height * 4)
            if len(data) != width * height * 4:
                return None
            frame = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
            return cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
    except Exception:
        return None


def benchmark():
    results = []

    for model_name, scales in MODELS:
        for scale in scales:
            for device in DEVICES:
                sr = dnn_superres.DnnSuperResImpl_create()
                try:
                    load_model(sr, model_name, scale)
                    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                    sr.setPreferableTarget(
                        cv2.dnn.DNN_TARGET_CPU if device == "cpu" else cv2.dnn.DNN_TARGET_OPENCL
                    )
                except Exception as e:
                    print(f"[!] Error cargando modelo {model_name}_x{scale} en {device}: {e}")
                    continue

                for input_w, input_h in INPUT_SIZES:
                    print(f"[*] Model: {model_name}_x{scale}, Device: {device}, Input: {input_w}x{input_h}")

                    times = []
                    frames_ok = 0
                    for i in range(30):
                        frame = read_frame(input_w, input_h)
                        if frame is None:
                            continue

                        start = time.time()
                        try:
                            result = sr.upsample(frame)
                        except Exception as e:
                            print(f"  [!] Error durante upsample: {e}")
                            break
                        end = time.time()

                        times.append((end - start) * 1000)  # en ms
                        frames_ok += 1

                    if frames_ok > 0:
                        avg_time = sum(times) / frames_ok
                        print(f"    -> Tiempo medio: {avg_time:.2f} ms/frame ({frames_ok} frames)")
                        results.append((model_name, scale, device, f"{input_w}x{input_h}", avg_time))
                    else:
                        print("    -> No se pudo capturar ningún frame válido")

    print("\nResumen:")
    for r in results:
        print(f"Modelo: {r[0]}_x{r[1]}, Dispositivo: {r[2]}, Entrada: {r[3]}, Tiempo medio: {r[4]:.2f} ms")


if __name__ == "__main__":
    benchmark()
