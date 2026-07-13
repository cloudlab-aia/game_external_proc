import subprocess
import time
import csv
import os
import signal

RESOLUTIONS = [
    (128, 72),
    (640, 360),
    (1280, 720),
    (1920, 1080),
    (2560, 1440)
]

OUTPUT_SIZE = (3840, 2160)  # 4K
MODEL_PATH = "./models/RealESRGAN_x4plus.pth"

def run_game(width, height):
    """Lanza glxgears en una ventana redimensionada"""
    return subprocess.Popen(
        ["bash", "-c", f"LD_PRELOAD=./frame_capture.so glxgears -geometry {width}x{height}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

def run_realesrgan(width, height, duration=10):
    """Ejecuta el script de inferencia y mide rendimiento"""
    cmd = [
        "python", "run_realesrgan.py",
        "--model", MODEL_PATH,
        "--upscale", "4",
        "--device", "cuda",  # usa cpu/opencl/cuda según tengas disponible
        "--duration", str(duration),
        "--output_w", str(OUTPUT_SIZE[0]),
        "--output_h", str(OUTPUT_SIZE[1])
    ]
    env = os.environ.copy()
    env["RES_WIDTH"] = str(width)
    env["RES_HEIGHT"] = str(height)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out, err = proc.communicate()
    return out, err

def main():
    results = []

    for w, h in RESOLUTIONS:
        print(f"\n=== Benchmark {w}x{h} ===")
        game_proc = run_game(w, h)
        time.sleep(2)  # esperar a que arranque

        out, err = run_realesrgan(w, h, duration=15)

        # parsear resultados desde run_realesrgan.py (última línea resumen)
        lines = out.strip().split("\n")
        last_line = lines[-1] if lines else ""
        print(last_line)

        # guardar en CSV
        results.append([w, h, last_line])

        # matar juego
        os.killpg(os.getpgid(game_proc.pid), signal.SIGTERM)
        time.sleep(1)

    with open("benchmark_realesrgan.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["InputWidth", "InputHeight", "Summary"])
        writer.writerows(results)

    print("\n[*] Benchmark completado. Resultados en benchmark_realesrgan.csv")

if __name__ == "__main__":
    main()
