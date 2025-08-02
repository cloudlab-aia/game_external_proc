import os
import cv2
import time
import numpy as np
import struct
import onnxruntime as ort

SHM_NAME = "/dev/shm/framebuffer_shared"
MODEL_ONNX = "/home/ogg/Desktop/AIA/game_external_proc/models/RealESRGAN_x4.onnx"

# Inicializar ONNX Runtime para Real-ESRGAN
try:
    ort_session = ort.InferenceSession(
        MODEL_ONNX,
        providers=['CPUExecutionProvider', 'OpenVINOExecutionProvider']
    )
    print(f"[INFO] Real-ESRGAN x4 ONNX model loaded: {MODEL_ONNX}")
except Exception as e:
    print(f"[ERROR] Failed to load Real-ESRGAN model: {e}")
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

def upscale_esrgan(frame_bgr, width, height):
    try:
        # Resize to model's expected input size
        input_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        input_img = cv2.resize(input_img, (224, 224), interpolation=cv2.INTER_CUBIC)
        input_img = input_img.astype(np.float32) / 255.0
        input_img = np.transpose(input_img, (2, 0, 1))[None, ...]  # [1, 3, 224, 224]
        input_img = np.ascontiguousarray(input_img)
        
        # Run inference
        outputs = ort_session.run(None, {"input": input_img})
        out_img = outputs[0][0]  # [3, H*scale, W*scale] or [3, 224, 224]
        out_img = np.clip(out_img * 255.0, 0, 255).astype(np.uint8)
        out_img = np.transpose(out_img, (1, 2, 0))  # [224, 224, 3]
        out_img_bgr = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
        
        # Optional: resize back to original size
        out_img_bgr = cv2.resize(out_img_bgr, (width, height), interpolation=cv2.INTER_CUBIC)
        
        return out_img_bgr
    except Exception as e:
        print(f"[ERROR] Fallo en superresolución: {e}")
        return cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_CUBIC)

if __name__ == "__main__":
    print("[INFO] Mostrando ventana Real-ESRGAN con IA. Pulsa 'q' para salir.")
    window_name = "AI Super-Resolution (Real-ESRGAN x4)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    while True:
        frame, width, height = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            start = time.time()
            upscaled = upscale_esrgan(frame, width, height)
            latency = (time.time() - start) * 1000
            cv2.setWindowTitle(window_name, f"AI Super-Resolution (Real-ESRGAN x4) - {latency:.1f} ms")
            cv2.resizeWindow(window_name, width, height)
            cv2.imshow(window_name, upscaled)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("[ERROR] Fallo durante inferencia:", e)
            time.sleep(0.1)
    cv2.destroyAllWindows()
