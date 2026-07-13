import os
import cv2
import time
import numpy as np
import struct

SHM_NAME = "/dev/shm/framebuffer_shared"
MODEL_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x2.pb"

# Inicializar modelo FSRCNN x2 con OpenCV
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(MODEL_PATH)
sr.setModel("fsrcnn", 2)
sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

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

def upscale_fsrcnn(frame_bgr):
    try:
        # El modelo acepta cualquier tamaño divisible entre 2
        return sr.upsample(frame_bgr)
    except Exception as e:
        print(f"[ERROR] Fallo en superresolución: {e}")
        return frame_bgr

if __name__ == "__main__":
    print("[INFO] Mostrando ventana FSRCNN x2. Pulsa 'q' para salir.")
    window_name = "AI Super-Resolution (FSRCNN x2)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    while True:
        frame, width, height = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            start = time.time()
            upscaled = upscale_fsrcnn(frame)
            latency = (time.time() - start) * 1000
            cv2.setWindowTitle(window_name, f"FSRCNN x2 - {latency:.1f} ms")
            cv2.resizeWindow(window_name, upscaled.shape[1], upscaled.shape[0])
            cv2.imshow(window_name, upscaled)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("[ERROR] Fallo durante inferencia:", e)
            time.sleep(0.1)
    cv2.destroyAllWindows()
