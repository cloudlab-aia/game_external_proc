import subprocess
import time
import os
from pathlib import Path

resolutions = [
    (128, 72),
    (640, 360),
    (1280, 720),
    (1920, 1080),
    (2560, 1440),
]

models = [
    "../models/FSRCNN_x2.pb",
    "../models/FSRCNN_x3.pb",
    "../models/FSRCNN_x4.pb",
   # "../models/RealESRGAN_x4.onnx",
]

benchmark_script = "benchmark_models.py"

output_width, output_height = 3840, 2160
devices = ["cpu", "opencl"]  # Agrega "npu" si tu benchmark lo soporta

for width, height in resolutions:
    print(f"===> Ejecutando glxgears a {width}x{height}")
    # Lanzar glxgears interceptado con LD_PRELOAD
    proc = subprocess.Popen(
        ["bash", "-c", f"LD_PRELOAD=./libswapcapture.so glxgears"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Esperar a que la ventana esté disponible
    time.sleep(2)

    # Cambiar tamaño de ventana con wmctrl
    try:
        subprocess.run(
            ["wmctrl", "-r", "glxgears", "-e", f"0,0,0,{width},{height}"],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error redimensionando la ventana glxgears")

    # Esperar más tiempo para asegurar el redibujado
    time.sleep(4)

    # (Opcional) Mostrar tamaño real de la ventana (requiere xdotool)
    try:
        win_id = subprocess.check_output(
            ["xdotool", "search", "--name", "glxgears"]
        ).decode().strip().split('\n')[0]
        win_geom = subprocess.check_output(
            ["xdotool", "getwindowgeometry", win_id]
        ).decode()
        print(f"Tamaño real de la ventana:\n{win_geom}")
    except Exception:
        print("No se pudo obtener el tamaño real de la ventana (requiere xdotool)")

    # Ejecutar benchmark para cada modelo
    for model_path in models:
        for device in devices:
            print(f"--> Ejecutando benchmark con modelo: {model_path} en {device}")
            try:
                subprocess.run(
                    [
                        "python3", benchmark_script,
                        "--model", model_path,
                        "--input_size", str(width), str(height),
                        "--output_size", str(output_width), str(output_height),
                        "--device", device
                    ],
                    check=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Error ejecutando benchmark con {model_path} en {device}: {e}")
            # Pequeño delay entre benchmarks
            time.sleep(1)

    proc.terminate()
    proc.wait()
    time.sleep(2)
