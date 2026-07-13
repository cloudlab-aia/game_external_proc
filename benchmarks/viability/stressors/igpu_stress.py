#!/usr/bin/env python3
"""
Generador de carga sostenida sobre la iGPU Intel via OpenVINO.
Corre en bucle hasta recibir SIGTERM/SIGINT. Mantiene la iGPU saturada con
inferencias grandes, sin imprimir nada por stdout para no ensuciar logs.
"""
import os
import sys
import signal
import time
import numpy as np

STOP = False


def _handler(signum, frame):
    global STOP
    STOP = True


def main():
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)

    import openvino as ov
    import cv2  # noqa: F401

    model_path = os.environ.get(
        "STRESS_MODEL",
        "/home/ogg/Desktop/TFG_CODE/models/RealESRGAN_x4.onnx",
    )
    shape_h = int(os.environ.get("STRESS_H", "512"))
    shape_w = int(os.environ.get("STRESS_W", "512"))

    core = ov.Core()
    model = core.read_model(model_path)
    inp = model.inputs[0]
    if inp.partial_shape[1].is_static:
        c = inp.partial_shape[1].get_length()
    else:
        c = 1
    try:
        model.reshape({inp.any_name: [1, c, shape_h, shape_w]})
    except Exception:
        pass

    compiled = core.compile_model(model, "GPU")
    req = compiled.create_infer_request()

    if c == 1:
        feed = {inp.any_name: np.random.rand(1, 1, shape_h, shape_w).astype(np.float32)}
    else:
        feed = {inp.any_name: np.random.rand(1, c, shape_h, shape_w).astype(np.float32)}

    # Senaliza disponibilidad
    sys.stdout.write("iGPU_STRESS_READY\n")
    sys.stdout.flush()

    while not STOP:
        req.infer(feed)


if __name__ == "__main__":
    main()
