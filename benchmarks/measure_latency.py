"""Mide la latencia end-to-end del pipeline híbrido (captura → pantalla).

Latencia, según el enunciado: tiempo desde que la dGPU genera el frame hasta
que se muestra por pantalla. Se mide con un sello de tiempo (CLOCK_MONOTONIC)
que el wrapper escribe en /dev/shm/framebuffer_ts al capturar cada frame; este
medidor lo lee y, tras procesar y presentar el frame, calcula:

    latencia_total = ahora − sello_de_captura

y un desglose por etapa: espera (captura→que el lector lo coge), inferencia IA
y presentación. Reporta media, p50, p95.

Requiere un juego/glxgears capturándose (cualquier pipeline de captura).
Uso:
    python3 benchmarks/measure_latency.py --frames 300 [--scale 4] [--no-display]
"""
import argparse
import os
import struct
import time

import cv2
import numpy as np
import openvino as ov

SHM = "/dev/shm/framebuffer_shared"
TS_SHM = "/dev/shm/framebuffer_ts"
HDR = "IIII"
HDR_SZ = struct.calcsize(HDR)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def now_ns():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def read_capture_ts():
    """Devuelve (seq, capture_ns) del buzón de sellos, o None."""
    try:
        with open(TS_SHM, "rb") as f:
            d = f.read(16)
        if len(d) < 16:
            return None
        seq = struct.unpack("<I", d[0:4])[0]
        ns = struct.unpack("<Q", d[8:16])[0]
        return seq, ns
    except FileNotFoundError:
        return None


def read_frame(last_seq):
    try:
        fd = os.open(SHM, os.O_RDONLY)
        try:
            h = os.read(fd, HDR_SZ)
            if len(h) < HDR_SZ:
                return None, last_seq
            w, ht, seq, ready = struct.unpack(HDR, h)
            if not ready or seq == last_seq or not (0 < w <= 8192 and 0 < ht <= 8192):
                return None, last_seq
            buf = os.read(fd, w * ht * 4)
            if len(buf) < w * ht * 4:
                return None, last_seq
        finally:
            os.close(fd)
        return cv2.cvtColor(np.frombuffer(buf, np.uint8).reshape((ht, w, 4)), cv2.COLOR_RGBA2BGR), seq
    except FileNotFoundError:
        return None, last_seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--no-display", action="store_true")
    args = ap.parse_args()

    in_w, in_h = {4: (480, 270), 3: (640, 360), 2: (960, 540)}[args.scale]
    core = ov.Core()
    dev = "GPU" if "GPU" in core.available_devices else "CPU"
    m = core.read_model(os.path.join(REPO, "models", "openvino_ir", f"FSRCNN_x{args.scale}.xml"))
    m.reshape([1, in_h, in_w, 1])
    infer = core.compile_model(m, dev, {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()
    print(f"[INFO] {dev}, FSRCNN x{args.scale}, display={'no' if args.no_display else 'sí'}")

    if read_capture_ts() is None:
        raise SystemExit("No hay sello de tiempo (/dev/shm/framebuffer_ts). "
                         "¿Está capturando el wrapper recompilado?")

    win = "latencia"
    if not args.no_display:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    tot, wait, infer_t, disp_t = [], [], [], []
    last_seq, n = 0, 0
    print("[INFO] Midiendo...")
    while n < args.frames:
        frame, seq = read_frame(last_seq)
        if frame is None:
            continue
        ts = read_capture_ts()
        if ts is None or ts[0] != seq:
            # el sello no corresponde a este frame (carrera); saltar
            last_seq = seq
            continue
        cap_ns = ts[1]
        last_seq = seq
        t0 = now_ns()                      # lector coge el frame

        ycrcb = cv2.cvtColor(cv2.resize(frame, (in_w, in_h)), cv2.COLOR_BGR2YCrCb)
        y = ycrcb[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
        infer.infer({0: y})
        yu = (np.squeeze(infer.get_output_tensor().data) * 255).clip(0, 255).astype(np.uint8)
        oh, ow = yu.shape
        cr = cv2.resize(ycrcb[:, :, 1], (ow, oh)); cb = cv2.resize(ycrcb[:, :, 2], (ow, oh))
        out = cv2.cvtColor(cv2.merge([yu, cr, cb]), cv2.COLOR_YCrCb2BGR)
        t1 = now_ns()                      # IA terminada

        if not args.no_display:
            cv2.imshow(win, out)
            cv2.waitKey(1)
        t2 = now_ns()                      # presentado

        wait.append((t0 - cap_ns) / 1e6)
        infer_t.append((t1 - t0) / 1e6)
        disp_t.append((t2 - t1) / 1e6)
        tot.append((t2 - cap_ns) / 1e6)
        n += 1

    if not args.no_display:
        cv2.destroyAllWindows()

    def stats(a):
        a = np.array(a)
        return a.mean(), np.percentile(a, 50), np.percentile(a, 95)

    print(f"\n=== Latencia captura→pantalla ({n} frames, {dev}, x{args.scale}) ===")
    print(f"{'etapa':<22}{'media':>9}{'p50':>9}{'p95':>9}  (ms)")
    for name, arr in [("espera captura→lector", wait), ("inferencia IA", infer_t),
                      ("presentación", disp_t), ("TOTAL", tot)]:
        mean, p50, p95 = stats(arr)
        print(f"{name:<22}{mean:>9.2f}{p50:>9.2f}{p95:>9.2f}")
    print("\nNota: mide hasta que la llamada de presentación retorna; la salida "
          "física a pantalla añade ~1 refresco del monitor.")


if __name__ == "__main__":
    main()
