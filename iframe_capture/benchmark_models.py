import cv2
import time
import numpy as np
import os
import argparse
from cv2 import dnn_superres
import csv

MODELS_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models"
SHM_PATH = "/dev/shm/framebuffer_shared"  # Imagen escrita por libswapcapture.so

def load_model(sr, model_path):
    # Detecta tipo de modelo
    if model_path.endswith(".pb"):
        # FSRCNN
        if "FSRCNN" in model_path.upper():
            scale = int(model_path.split("_x")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("fsrcnn", scale)
        else:
            raise ValueError("Modelo .pb no reconocido")
    elif model_path.endswith(".onnx"):
        # RealESRGAN (no soportado por OpenCV dnn_superres, solo ejemplo)
        sr.readModel(model_path)
        sr.setModel("edsr", 4)  # EDSR es lo más parecido, escala 4x
    else:
        raise ValueError("Modelo no soportado")

def read_frame(expected_width, expected_height):
    try:
        with open(SHM_PATH, 'rb') as f:
            header = f.read(8)
            if len(header) != 8:
                return None
            width = int.from_bytes(header[:4], 'little')
            height = int.from_bytes(header[4:8], 'little')
            if width != expected_width or height != expected_height:
                # No hay frame válido para esta resolución
                return None
            data = f.read(width * height * 4)
            if len(data) != width * height * 4:
                return None
            frame = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
            return cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
    except Exception:
        return None

def wait_for_frame(expected_width, expected_height, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        frame = read_frame(expected_width, expected_height)
        if frame is not None:
            return frame
        time.sleep(0.1)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Ruta al modelo (.pb o .onnx)")
    parser.add_argument("--input_size", nargs=2, type=int, required=True, help="Resolución de entrada (ancho alto)")
    parser.add_argument("--output_size", nargs=2, type=int, required=True, help="Resolución de salida (ancho alto)")
    parser.add_argument("--device", choices=["cpu", "opencl", "npu"], default="cpu", help="Dispositivo de inferencia")
    args = parser.parse_args()

    input_w, input_h = args.input_size
    output_w, output_h = args.output_size

    sr = dnn_superres.DnnSuperResImpl_create()
    try:
        load_model(sr, args.model)
        sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
        if args.device == "cpu":
            sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        elif args.device == "opencl":
            sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
        else:
            print("[!] NPU no soportado directamente por OpenCV dnn_superres")
            return
    except Exception as e:
        print(f"[!] Error cargando modelo {args.model} en {args.device}: {e}")
        return

    print(f"[*] Model: {os.path.basename(args.model)}, Device: {args.device}, Input: {input_w}x{input_h}, Output: {output_w}x{output_h}")

    times = []
    frames_ok = 0
    result_file = "benchmark_results.csv"
    result_exists = os.path.isfile(result_file)

    for i in range(30):
        frame = wait_for_frame(input_w, input_h)
        if frame is None:
            continue

        # Redimensiona la entrada si es necesario
        if frame.shape[1] != input_w or frame.shape[0] != input_h:
            frame = cv2.resize(frame, (input_w, input_h), interpolation=cv2.INTER_LINEAR)

        start = time.time()
        try:
            result = sr.upsample(frame)
            # Redimensiona la salida a 4K si el modelo no lo hace
            if result.shape[1] != output_w or result.shape[0] != output_h:
                result = cv2.resize(result, (output_w, output_h), interpolation=cv2.INTER_LINEAR)
            # Mostrar cada frame de salida
            cv2.imshow(f"Resultado {os.path.basename(args.model)} {args.device} {input_w}x{input_h}", result)
            # Espera 1 ms, si se pulsa una tecla, sale del bucle
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print(f"  [!] Error durante upsample: {e}")
            break
        end = time.time()

        times.append((end - start) * 1000)  # en ms
        frames_ok += 1

    cv2.destroyAllWindows()

    if frames_ok > 0:
        avg_time = sum(times) / frames_ok
        print(f"    -> Tiempo medio: {avg_time:.2f} ms/frame ({frames_ok} frames)")
        # Guardar en CSV
        with open(result_file, "a", newline="") as f:
            writer = csv.writer(f)
            if not result_exists:
                writer.writerow(["model", "device", "input_w", "input_h", "output_w", "output_h", "avg_time_ms", "frames"])
            writer.writerow([
                os.path.basename(args.model),
                args.device,
                input_w,
                input_h,
                output_w,
                output_h,
                round(avg_time, 2),
                frames_ok
            ])
    else:
        print("    -> No se pudo capturar ningún frame válido")

if __name__ == "__main__":
    main()
