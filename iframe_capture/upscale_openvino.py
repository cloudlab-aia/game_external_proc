import os
import cv2
import time
import numpy as np
import cv2.dnn_superres as dnn_sr
import struct

SHM_NAME = "/dev/shm/framebuffer_shared"

# === Inicializar OpenCV DNN Super Resolution ===
try:
    sr = dnn_sr.DnnSuperResImpl_create()
    UPSCALE_FACTOR = 4
    model_path = f"FSRCNN_x{UPSCALE_FACTOR}.pb"
    sr.readModel(model_path)
    sr.setModel("fsrcnn", UPSCALE_FACTOR)
    print(f"[INFO] FSRCNN x{UPSCALE_FACTOR} model loaded: {model_path}")
except Exception as e:
    print(f"[ERROR] Failed to load FSRCNN model: {e}")
    exit(1)

def get_shared_frame():
    try:
        with open(SHM_NAME, "rb") as f:
            header = f.read(8)
            width, height = struct.unpack("II", header)
            frame_data = f.read(width * height * 4)
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 4))
            frame_rgb = frame[:, :, :3]
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            frame_bgr = cv2.flip(frame_bgr, 0)
            return frame_bgr, width, height
    except Exception as e:
        print("[WARN] Error al leer frame compartido:", e)
        return None, None, None

def upscale_openvino(frame_bgr, width, height):
    try:
        input_size = (width // 4, height // 4)
        frame_small = cv2.resize(frame_bgr, input_size)
        upscaled = sr.upsample(frame_small)
        return upscaled
    except Exception as e:
        print(f"[ERROR] Fallo en superresolución: {e}")
        return cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_CUBIC)

if __name__ == "__main__":
    print("[INFO] Mostrando ventana OpenVINO con IA. Pulsa 'q' para salir.")
    window_name = "AI Super-Resolution (FSRCNN x4) - Dinámico"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    while True:
        frame, width, height = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            upscaled = upscale_openvino(frame, width, height)
            cv2.resizeWindow(window_name, width, height)
            cv2.imshow(window_name, upscaled)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("[ERROR] Fallo durante inferencia:", e)
            time.sleep(0.1)
    cv2.destroyAllWindows()
