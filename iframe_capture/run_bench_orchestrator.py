#!/usr/bin/env python3
import subprocess
import time
import os
import signal
from pathlib import Path

resolutions = [
    (128,72),
    (640,360),
    (1280,720),
    (1920,1080),
    (2560,1440),
]

models = [
    "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x2.pb",
    "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x3.pb",
    "/home/ogg/Desktop/AIA/game_external_proc/models/FSRCNN_x4.pb",
    "/home/ogg/Desktop/AIA/game_external_proc/models/RealESRGAN_x4.onnx",  # si existe
]

benchmark_script = "benchmark_models.py"
output_width, output_height = 3840, 2160
devices = ["cpu","opencl"]  # añade "npu" si tu benchmark.py soporta y tienes runtime

lib_preload = "./libswapcapture.so"  # ruta al .so compilado

def run_glxgears_with_preload():
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(Path(lib_preload).resolve())
    # redirigimos salida para no contaminar logs
    p = subprocess.Popen(["glxgears"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p

for w,h in resolutions:
    print(f"===> Resolución test: {w}x{h}")
    p = run_glxgears_with_preload()
    # give time to start
    time.sleep(2.5)

    # try to resize window (may require wmctrl and that the window name contains 'glxgears')
    try:
        subprocess.run(["wmctrl","-r","glxgears","-e",f"0,0,0,{w},{h}"], check=True)
    except Exception as e:
        print(f"[!] wmctrl no funcionó: {e} — asegúrate de tener wmctrl y que exista ventana 'glxgears'")

    # wait to stabilize
    time.sleep(3.5)

    # for each model/device run benchmark
    for model_path in models:
        if not os.path.exists(model_path):
            print(f"  [!] Modelo no encontrado: {model_path}, saltando")
            continue
        for device in devices:
            print(f"  --> Ejecutando: model={model_path} device={device} input={w}x{h}")
            try:
                subprocess.run([
                    "python3", benchmark_script,
                    "--model", model_path,
                    "--input_size", str(w), str(h),
                    "--output_size", str(output_width), str(output_height),
                    "--device", device,
                    "--save_example"
                ], check=True)
            except subprocess.CalledProcessError as e:
                print(f"    [!] Error corriendo benchmark: {e}")
            # pequeño descanso
            time.sleep(1.0)

    # terminar glxgears
    try:
        p.terminate()
        p.wait(timeout=3)
    except Exception:
        p.kill()
    time.sleep(1.5)
