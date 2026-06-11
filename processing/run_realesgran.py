import mmap
import struct
import numpy as np
import cv2
import time
import torch
from realesrgan import RealESRGANer
import csv

SHM_PATH = "/dev/shm/framebuffer_shared"

# === Configuración del modelo ===
MODEL_PATH = "./models/RealESRGAN_x4plus.pth"  # coloca aquí el modelo descargado
UPSCALE = 4
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Inicializar Real-ESRGAN
upsampler = RealESRGANer(
    scale=UPSCALE,
    model_path=MODEL_PATH,
    dni_weight=None,
    device=DEVICE,
    half=True
)

def read_frame_from_shm():
    with open(SHM_PATH, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)
        width, height = struct.unpack("ii", mm[0:8])
        frame_data = mm[8:]
        img = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 4))
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        img = cv2.flip(img, 0)  # invertir verticalmente
        mm.close()
    return img, width, height

def main():
    results = []
    prev_time = time.time()
    frame_count = 0

    while True:
        try:
            # === Captura ===
            t0 = time.time()
            frame, w, h = read_frame_from_shm()
            t1 = time.time()
            capture_time = (t1 - t0) * 1000  # ms

            # === Inferencia ===
            t2 = time.time()
            output, _ = upsampler.enhance(frame, outscale=UPSCALE)
            t3 = time.time()
            inference_time = (t3 - t2) * 1000  # ms

            # === FPS ===
            frame_count += 1
            now = time.time()
            elapsed = now - prev_time
            fps = frame_count / elapsed if elapsed > 0 else 0

            # === Mostrar ===
            cv2.imshow("Upscaled", output)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            # === Guardar métricas ===
            results.append([w, h, round(capture_time, 2), round(inference_time, 2), round(fps, 2)])

        except Exception as e:
            print("Esperando frames...", e)
            time.sleep(0.5)

    cv2.destroyAllWindows()

    # === Guardar CSV ===
    with open("realesrgan_bench.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Width", "Height", "CaptureTime(ms)", "InferenceTime(ms)", "FPS"])
        writer.writerows(results)

    print("[*] Resultados guardados en realesrgan_bench.csv")

if __name__ == "__main__":
    main()
