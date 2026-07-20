#!/usr/bin/env python3
"""Medida honesta del sistema final: para un dispositivo de inferencia,
ejecuta el PIPELINE COMPLETO del consumidor (lectura, preproceso,
inferencia, POSTPROCESO de color y reescalado a la salida) igual que
display_overlay_forward.py, y reporta dos metricas distintas:

  - render_fps : FPS de RENDER del juego (delta del contador de secuencia
                 de la shm). Mide si la arquitectura libera la dGPU.
  - visible_fps: FPS que el consumidor produce de verdad (frames que
                 completan todo el pipeline por segundo). Es lo que el
                 jugador veria en pantalla.

Con --display muestra la salida en pantalla (incluye el coste de present).
Sin el, hace todo el trabajo salvo el imshow (mide throughput de computo).

Uso:  CUDA_VISIBLE_DEVICES="" python3 experiments/measure_system_final.py \
          --device iGPU --scale 3 --out_w 1920 --out_h 1080 \
          --measure_secs 12 --warmup_secs 4
"""
import argparse
import os
import struct
import time

import cv2
import numpy as np

SHM = "/dev/shm/framebuffer_shared"
HDR = "IIII"
HSZ = struct.calcsize(HDR)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_latest(last_seq):
    """Lee SIEMPRE el frame mas reciente (salta frames si el consumidor
    va por detras), devolviendo tambien el seq para medir el render."""
    try:
        fd = os.open(SHM, os.O_RDONLY)
        try:
            h = os.read(fd, HSZ)
            if len(h) < HSZ:
                return None, last_seq, last_seq
            w, ht, seq, ready = struct.unpack(HDR, h)
            cur_seq = seq
            if not ready or not (0 < w <= 8192 and 0 < ht <= 8192):
                return None, last_seq, cur_seq
            if seq == last_seq:
                return None, last_seq, cur_seq  # no hay frame nuevo
            buf = os.read(fd, w * ht * 4)
            if len(buf) < w * ht * 4:
                return None, last_seq, cur_seq
        finally:
            os.close(fd)
        img = cv2.cvtColor(np.frombuffer(buf, np.uint8).reshape((ht, w, 4)),
                           cv2.COLOR_RGBA2BGR)
        return img, seq, cur_seq
    except FileNotFoundError:
        return None, last_seq, last_seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True, choices=["iGPU", "dGPU"])
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--in_w", type=int, default=640)
    ap.add_argument("--in_h", type=int, default=360)
    ap.add_argument("--out_w", type=int, default=1920)
    ap.add_argument("--out_h", type=int, default=1080)
    ap.add_argument("--measure_secs", type=float, default=12)
    ap.add_argument("--warmup_secs", type=float, default=4)
    ap.add_argument("--display", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    # backend de inferencia
    if args.device == "iGPU":
        import openvino as ov
        core = ov.Core()
        m = core.read_model(os.path.join(REPO, "models", "openvino_ir",
                                         f"FSRCNN_x{args.scale}.xml"))
        m.reshape([1, args.in_h, args.in_w, 1])
        req = core.compile_model(m, "GPU",
                                 {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()
        def infer(y):
            req.infer({0: y})
            return np.squeeze(req.get_output_tensor().data)
    else:
        import onnxruntime as ort
        ort.preload_dlls()
        s = ort.InferenceSession(
            os.path.join(REPO, "models", f"FSRCNN_x{args.scale}.onnx"),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        assert s.get_providers()[0] == "CUDAExecutionProvider", "CUDA no activo"
        name = s.get_inputs()[0].name
        out_name = s.get_outputs()[0].name
        def infer(y):
            return np.squeeze(s.run([out_name], {name: y})[0])

    if args.display:
        cv2.namedWindow("salida", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("salida", args.out_w, args.out_h)

    print(f"[medida] {args.device} FSRCNN x{args.scale} "
          f"{args.in_w}x{args.in_h} -> {args.out_w}x{args.out_h}, "
          f"pipeline COMPLETO{' + display' if args.display else ''}")

    last_seq = 0
    first_seq = None
    max_seq = 0
    processed = 0
    t_warm_end = time.perf_counter() + args.warmup_secs
    t_start = None
    t_end = None
    while True:
        frame, seq, cur_seq = read_latest(last_seq)
        if cur_seq > max_seq:
            max_seq = cur_seq
        if frame is None:
            time.sleep(0.0005)
            now = time.perf_counter()
            if t_start is not None and now >= t_end:
                break
            continue
        last_seq = seq

        # --- pipeline completo (identico a display_overlay_forward) ---
        ycc = cv2.cvtColor(cv2.resize(frame, (args.in_w, args.in_h)),
                           cv2.COLOR_BGR2YCrCb)
        y = ycc[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
        y_sr = infer(y)
        y8 = np.clip(y_sr * 255.0, 0, 255).astype(np.uint8)
        oh, ow = y8.shape
        cr = cv2.resize(ycc[:, :, 1], (ow, oh), interpolation=cv2.INTER_CUBIC)
        cb = cv2.resize(ycc[:, :, 2], (ow, oh), interpolation=cv2.INTER_CUBIC)
        out = cv2.cvtColor(cv2.merge([y8, cr, cb]), cv2.COLOR_YCrCb2BGR)
        if (ow, oh) != (args.out_w, args.out_h):
            out = cv2.resize(out, (args.out_w, args.out_h),
                             interpolation=cv2.INTER_CUBIC)
        if args.display:
            cv2.imshow("salida", out)
            cv2.waitKey(1)

        now = time.perf_counter()
        if t_start is None and now >= t_warm_end:
            t_start = now
            t_end = now + args.measure_secs
            first_seq = cur_seq
            processed = 0
        elif t_start is not None:
            processed += 1
            if now >= t_end:
                break

    elapsed = time.perf_counter() - t_start
    render_fps = (max_seq - first_seq) / elapsed
    visible_fps = processed / elapsed
    print(f"RESULT tag={args.tag} device={args.device} in={args.in_w}x{args.in_h} "
          f"render_fps={render_fps:.2f} visible_fps={visible_fps:.2f} "
          f"elapsed={elapsed:.1f}")


if __name__ == "__main__":
    main()
