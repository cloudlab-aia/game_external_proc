"""Consumidor de upscaling headless: lee frames del buzón y los reescala con
FSRCNN en el dispositivo indicado, en bucle, sin mostrar nada. Sirve para
cargar ese dispositivo con la tarea de IA mientras se mide el FPS del juego.

  --device iGPU  -> OpenVINO GPU (Intel)   = configuración HÍBRIDA
  --device dGPU  -> ONNX Runtime CUDA      = configuración DEDICADA (compite con el render)

Uso:  python3 experiments/upscale_consumer.py --device dGPU --scale 4
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


def read_frame(last_seq):
    try:
        fd = os.open(SHM, os.O_RDONLY)
        try:
            h = os.read(fd, HSZ)
            if len(h) < HSZ:
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
    ap.add_argument("--device", required=True, choices=["iGPU", "dGPU"])
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--in_w", type=int, default=480)
    ap.add_argument("--in_h", type=int, default=270)
    ap.add_argument("--measure_secs", type=float, default=0,
                    help="Si >0: tras un calentamiento, mide el ritmo de salida "
                         "(frames reescalados/s = FPS final) durante N s y termina.")
    ap.add_argument("--warmup_secs", type=float, default=3)
    ap.add_argument("--passes", type=int, default=1,
                    help="Inferencias por frame. Simula un modelo N veces más "
                         "pesado (mando de complejidad de la IA).")
    args = ap.parse_args()

    if args.device == "iGPU":
        import openvino as ov
        core = ov.Core()
        m = core.read_model(os.path.join(REPO, "models", "openvino_ir", f"FSRCNN_x{args.scale}.xml"))
        m.reshape([1, args.in_h, args.in_w, 1])
        req = core.compile_model(m, "GPU", {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()
        def infer(y): req.infer({0: y})
    else:
        import onnxruntime as ort
        ort.preload_dlls()
        s = ort.InferenceSession(os.path.join(REPO, "models", f"FSRCNN_x{args.scale}.onnx"),
                                 providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        assert s.get_providers()[0] == "CUDAExecutionProvider", "CUDA no activo"
        name = s.get_inputs()[0].name
        def infer(y): s.run(None, {name: y})

    print(f"[consumer] FSRCNN x{args.scale} en {args.device}, procesando frames...")
    last_seq, n = 0, 0
    t_end = None            # fin de la ventana de medida
    t_measure_start = None  # inicio de la ventana (tras calentamiento)
    n_measure = 0
    if args.measure_secs > 0:
        t_warmup_end = time.perf_counter() + args.warmup_secs
    while True:
        frame, seq = read_frame(last_seq)
        if frame is None:
            time.sleep(0.001)
            continue
        last_seq = seq
        y = cv2.cvtColor(cv2.resize(frame, (args.in_w, args.in_h)), cv2.COLOR_BGR2YCrCb)[:, :, 0]
        yin = y.astype(np.float32)[None, :, :, None] / 255.0
        for _ in range(args.passes):   # N pasadas = modelo N veces más pesado
            infer(yin)
        n += 1
        if args.measure_secs > 0:
            now = time.perf_counter()
            if t_measure_start is None and now >= t_warmup_end:
                t_measure_start = now
                t_end = now + args.measure_secs
                n_measure = 0
            elif t_measure_start is not None:
                n_measure += 1
                if now >= t_end:
                    fps = n_measure / (now - t_measure_start)
                    print(f"OUTPUT_FPS={fps:.2f}")
                    return


if __name__ == "__main__":
    main()
