#!/usr/bin/env python3
"""Benchmark de captura: wrapper LD_PRELOAD vs VirtualGL modificado.

Mide:
- FPS de captura: incremento del contador seq del header shm por segundo
- FPS de la app: salida de glxgears (frames en 5.0 seconds = X FPS)
"""
import os
import re
import signal
import struct
import subprocess
import sys
import time

SHM = "/dev/shm/framebuffer_shared"
HEADER_FMT = "IIII"  # width, height, seq, ready


def read_seq():
    try:
        with open(SHM, "rb") as f:
            data = f.read(struct.calcsize(HEADER_FMT))
            if len(data) < struct.calcsize(HEADER_FMT):
                return None
            w, h, seq, ready = struct.unpack(HEADER_FMT, data)
            return w, h, seq
    except FileNotFoundError:
        return None


def run_case(label, width, height, extra_env, preload, warmup=4.0, duration=10.0):
    if os.path.exists(SHM):
        os.unlink(SHM)

    env = os.environ.copy()
    env.update(extra_env)
    env["DISPLAY"] = ":1"
    env["__GL_SYNC_TO_VBLANK"] = "0"  # sin vsync (NVIDIA)
    env["vblank_mode"] = "0"          # sin vsync (Mesa)
    if preload:
        env["LD_PRELOAD"] = preload

    cmd = ["glxgears", "-geometry", f"{width}x{height}"]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    time.sleep(warmup)

    start = read_seq()
    t0 = time.time()
    time.sleep(duration)
    end = read_seq()
    t1 = time.time()

    proc.send_signal(signal.SIGINT)
    try:
        out, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()

    # FPS de glxgears: media de las líneas "X frames in 5.0 seconds = Y FPS"
    app_fps_samples = [float(m) for m in re.findall(r"= ([\d.]+) FPS", out)]
    app_fps = sum(app_fps_samples) / len(app_fps_samples) if app_fps_samples else 0.0

    if start is None or end is None:
        cap_fps = 0.0
        res = "sin captura"
    else:
        cap_fps = (end[2] - start[2]) / (t1 - t0)
        res = f"{end[0]}x{end[1]}"

    print(f"{label:24s} {width}x{height:<6} app={app_fps:9.1f} FPS  "
          f"captura={cap_fps:9.1f} FPS  shm={res}")
    return app_fps, cap_fps


if __name__ == "__main__":
    repo = "/home/ogg/Desktop/AIA/game_external_proc"
    vgl_lib = f"{repo}/virtualgl/build/lib"
    vgl_env = {
        "VGL_DISPLAY": ":1",
        "LD_LIBRARY_PATH": f"{vgl_lib}:/tmp/tjpeg/usr/lib/x86_64-linux-gnu",
        "VGL_LOGO": "0",
    }

    results = []
    for w, h in [(640, 360), (1280, 720), (1920, 1080)]:
        a = run_case("baseline (sin captura)", w, h, {}, None)
        b = run_case("wrapper LD_PRELOAD", w, h, {}, "/tmp/wrapper_shm.so")
        c = run_case("VirtualGL modificado", w, h, vgl_env,
                     f"{vgl_lib}/libdlfaker.so:{vgl_lib}/libvglfaker.so")
        results.append((f"{w}x{h}", a, b, c))
        print()

    print("== CSV ==")
    print("resolucion,baseline_app_fps,wrapper_app_fps,wrapper_cap_fps,vgl_app_fps,vgl_cap_fps")
    for res, a, b, c in results:
        print(f"{res},{a[0]:.1f},{b[0]:.1f},{b[1]:.1f},{c[0]:.1f},{c[1]:.1f}")
