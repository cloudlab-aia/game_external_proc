#!/usr/bin/env python3
"""Prototipo de pipeline SOLAPADO (doble buffer), aparte de la medida
oficial secuencial (measure_system_final.py, sin tocar).

Hilo productor: lee shm, preprocesa, infiere -> deja el resultado en un
buffer de 1 hueco (se sobreescribe si el consumidor va por detras).
Hilo consumidor (principal): coge el ultimo resultado, hace el
postprocesado (resize croma + merge + color) y presenta.

Mientras el consumidor postprocesa/presenta el frame N, el productor ya
esta infiriendo el frame N+1: el tiempo total pasa a ser el MAXIMO de
las dos etapas en vez de la SUMA, que es la mejora de "trabajo futuro"
estimada en el TFG a partir del desglose del Experimento de latencia.

Uso:  venv/bin/python3 experiments/measure_pipelined.py \
          --device iGPU --scale 4 --in_w 480 --in_h 270 \
          --out_w 1920 --out_h 1080 --measure_secs 10 --display
"""
import argparse
import os
import queue
import struct
import threading
import time

import cv2
import numpy as np

SHM = "/dev/shm/framebuffer_shared"
HDR = "IIII"
HSZ = struct.calcsize(HDR)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_latest(last_seq):
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
                return None, last_seq, cur_seq
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

    print(f"[medida-pipeline] {args.device} FSRCNN x{args.scale} "
          f"{args.in_w}x{args.in_h} -> {args.out_w}x{args.out_h}, "
          f"productor(infer) || consumidor(postpro+display)")

    slot = queue.Queue(maxsize=1)
    stop_flag = threading.Event()
    max_seq_holder = {"v": 0}

    def producer():
        last_seq = 0
        while not stop_flag.is_set():
            frame, seq, cur_seq = read_latest(last_seq)
            if cur_seq > max_seq_holder["v"]:
                max_seq_holder["v"] = cur_seq
            if frame is None:
                time.sleep(0.0005)
                continue
            last_seq = seq
            ycc = cv2.cvtColor(cv2.resize(frame, (args.in_w, args.in_h)),
                               cv2.COLOR_BGR2YCrCb)
            y = ycc[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
            y_sr = infer(y)
            if slot.full():
                try:
                    slot.get_nowait()
                except queue.Empty:
                    pass
            slot.put((ycc, y_sr))

    prod_thread = threading.Thread(target=producer, daemon=True)
    prod_thread.start()

    processed = 0
    t_warm_end = time.perf_counter() + args.warmup_secs
    t_start = None
    t_end = None
    first_max_seq = None
    while True:
        try:
            ycc, y_sr = slot.get(timeout=0.5)
        except queue.Empty:
            now = time.perf_counter()
            if t_start is not None and now >= t_end:
                break
            continue

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
            first_max_seq = max_seq_holder["v"]
            processed = 0
        elif t_start is not None:
            processed += 1
            if now >= t_end:
                break

    stop_flag.set()
    prod_thread.join(timeout=2)

    elapsed = time.perf_counter() - t_start
    render_fps = (max_seq_holder["v"] - first_max_seq) / elapsed
    visible_fps = processed / elapsed
    print(f"RESULT tag={args.tag} device={args.device} in={args.in_w}x{args.in_h} "
          f"render_fps={render_fps:.2f} visible_fps={visible_fps:.2f} "
          f"elapsed={elapsed:.1f} PIPELINED")


if __name__ == "__main__":
    main()
