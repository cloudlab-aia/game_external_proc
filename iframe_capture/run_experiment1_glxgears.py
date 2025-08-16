#!/usr/bin/env python3
import subprocess
import time
import os
import argparse
from pathlib import Path

# Configuración
SHM_PATH = "/dev/shm/framebuffer_shared"

def wait_for_shm_frame(width, height, timeout=5.0):
    """Espera a que aparezca un frame con el tamaño esperado en la shm"""
    import struct
    import numpy as np
    HEADER_FMT = "IIII"
    HEADER_SIZE = struct.calcsize(HEADER_FMT)

    start = time.time()
    last_seq = 0
    while time.time() - start < timeout:
        if not os.path.exists(SHM_PATH):
            time.sleep(0.05)
            continue
        with open(SHM_PATH, "rb") as f:
            header = f.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                time.sleep(0.05)
                continue
            w, h, seq, ready = struct.unpack(HEADER_FMT, header)
            if ready != 1 or seq == last_seq:
                time.sleep(0.02)
                continue
            if w == width and h == height:
                return True
        time.sleep(0.02)
    return False

def resize_glxgears_window(width, height):
    """Redimensiona la ventana glxgears usando xdotool"""
    try:
        win_id = subprocess.check_output(
            ["xdotool", "search", "--name", "glxgears"]
        ).decode().strip().split("\n")[0]
        subprocess.run(["xdotool", "windowsize", win_id, str(width), str(height)], check=True)
        time.sleep(0.5)  # Espera a que se redibuje
        return True
    except Exception as e:
        print(f"Error redimensionando la ventana: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True, help="Lista de modelos .pb o .onnx")
    parser.add_argument("--resolutions", nargs="+", type=int, required=True, help="Lista de resoluciones input W H, ej: 128 72 640 360 ...")
    parser.add_argument("--output_size", nargs=2, type=int, required=True, help="Output size W H")
    parser.add_argument("--device", choices=["cpu","opencl","npu"], default="cpu")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--save_example", action="store_true")
    args = parser.parse_args()

    output_w, output_h = args.output_size
    resolutions = [(args.resolutions[i], args.resolutions[i+1]) for i in range(0,len(args.resolutions),2)]
    
    benchmark_script = Path(__file__).parent / "benchmark_models.py"

    for width, height in resolutions:
        print(f"\n=== Resolución entrada: {width}x{height} ===")
        # Lanzar glxgears con LD_PRELOAD
        proc = subprocess.Popen(
            ["bash", "-c", f"LD_PRELOAD=./libswapcapture.so glxgears"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Esperar ventana y redimensionar
        time.sleep(1.5)
        if not resize_glxgears_window(width, height):
            print("No se pudo redimensionar la ventana, se continuará con tamaño por defecto")

        # Esperar primer frame
        if not wait_for_shm_frame(width, height, timeout=5.0):
            print("    [!] No se detectó frame en shm para esta resolución")
        
        # Ejecutar benchmark para cada modelo
        for model_path in args.models:
            print(f"--> Benchmark modelo: {model_path} en {args.device}")
            cmd = [
                "python3", str(benchmark_script),
                "--model", model_path,
                "--input_size", str(width), str(height),
                "--output_size", str(output_w), str(output_h),
                "--device", args.device
            ]
            if args.warmup:
                cmd += ["--warmup", str(args.warmup)]
            if args.iters:
                cmd += ["--iters", str(args.iters)]
            if args.save_example:
                cmd += ["--save_example"]
            subprocess.run(cmd, check=True)

        # Terminar glxgears
        proc.terminate()
        proc.wait()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
