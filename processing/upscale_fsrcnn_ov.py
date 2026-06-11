"""Superresolución en tiempo real con FSRCNN sobre OpenVINO (iGPU Intel).

Lee frames de /dev/shm/framebuffer_shared (formato con header) y los reescala
a 1080p. FSRCNN trabaja solo sobre el canal de luminancia (Y); el croma se
reescala con bicúbico, que es la práctica estándar en superresolución y
mantiene la latencia baja.

Frente a upscale_display.py (modelo sisr-1032, ~63 ms/frame), esta vía mide
~13 ms/frame (FSRCNN x4) gracias a un modelo mucho más ligero y a entrada de
un solo canal a baja resolución. Variables de entorno:

  FSRCNN_SCALE   = 4 (def) | 2     factor de escala / modelo IR a usar
  IGPU_MONITOR_X = 0 (def)          offset X del monitor donde abrir la ventana
"""
import os
import struct
import time

import cv2
import numpy as np
import openvino as ov

SHM_NAME = "/dev/shm/framebuffer_shared"
HEADER_FMT = "IIII"   # width, height, seq, ready
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_DIM = 8192

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = int(os.environ.get("FSRCNN_SCALE", "4"))
MODEL_XML = os.path.join(REPO_DIR, "models", f"fsrcnn_x{SCALE}_ov.xml")
# Resolución de entrada del modelo IR (debe coincidir con la usada al guardarlo)
IN_W, IN_H = (480, 270) if SCALE == 4 else (960, 540)

core = ov.Core()
device = "GPU" if "GPU" in core.available_devices else "CPU"
print(f"[INFO] Dispositivos: {core.available_devices} → usando {device}")
print(f"[INFO] Modelo: {MODEL_XML} (entrada {IN_W}x{IN_H}, escala x{SCALE})")

config = {"CACHE_DIR": "/tmp/openvino_cache"}
compiled = core.compile_model(core.read_model(MODEL_XML), device, config)
out_port = compiled.output(0)
# Cola asíncrona: una petición en vuelo mientras la CPU prepara la siguiente
infer = compiled.create_infer_request()


def read_frame(last_seq):
    """Devuelve (frame_bgr, seq) si hay frame nuevo, o (None, last_seq)."""
    try:
        fd = os.open(SHM_NAME, os.O_RDONLY)
        try:
            header = os.read(fd, HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                return None, last_seq
            w, h, seq, ready = struct.unpack(HEADER_FMT, header)
            if not ready or seq == last_seq or not (0 < w <= MAX_DIM and 0 < h <= MAX_DIM):
                return None, last_seq
            buf = os.read(fd, w * h * 4)
            if len(buf) < w * h * 4:
                return None, last_seq
        finally:
            os.close(fd)
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4))
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR), seq
    except FileNotFoundError:
        return None, last_seq


def upscale(frame_bgr):
    """FSRCNN sobre Y + croma bicúbico → BGR a IN*SCALE."""
    small = cv2.resize(frame_bgr, (IN_W, IN_H))
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
    infer.infer({0: y})
    y_up = (infer.get_output_tensor().data[0, 0] * 255).clip(0, 255).astype(np.uint8)
    oh, ow = y_up.shape
    cr = cv2.resize(ycrcb[:, :, 1], (ow, oh))
    cb = cv2.resize(ycrcb[:, :, 2], (ow, oh))
    return cv2.cvtColor(cv2.merge([y_up, cr, cb]), cv2.COLOR_YCrCb2BGR)


def main():
    win = f"AI Upscaling (FSRCNN x{SCALE} + OpenVINO) - {device}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.moveWindow(win, int(os.environ.get("IGPU_MONITOR_X", 0)), 0)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("[INFO] Esperando frames... 'q' para salir.")
    last_seq, n, acc = 0, 0, 0.0
    while True:
        frame, seq = read_frame(last_seq)
        if frame is None:
            time.sleep(0.002)
            continue
        last_seq = seq
        t0 = time.time()
        result = upscale(frame)
        acc += (time.time() - t0) * 1000
        n += 1
        if n % 60 == 0:
            avg = acc / 60
            print(f"[INFO] {n} frames: {avg:.1f} ms/frame (~{1000/avg:.0f} FPS)")
            acc = 0.0
        cv2.imshow(win, result)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
