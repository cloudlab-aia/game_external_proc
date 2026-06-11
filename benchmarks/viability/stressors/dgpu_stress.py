#!/usr/bin/env python3
"""
Generador de carga sostenida sobre la dGPU (NVIDIA RTX 5060) via ONNX Runtime CUDA.
Corre en bucle hasta recibir SIGTERM. Usa un modelo pesado para ocupar la GPU.
"""
import os
import sys
import signal
import numpy as np

STOP = False


def _handler(signum, frame):
    global STOP
    STOP = True


def main():
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)

    import onnxruntime as ort

    model_path = os.environ.get(
        "STRESS_MODEL",
        "/home/ogg/Desktop/TFG_CODE/models/RealESRGAN_x4.onnx",
    )

    sess = ort.InferenceSession(
        model_path,
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    if "CUDAExecutionProvider" not in sess.get_providers():
        print(f"[dgpu_stress] CUDA no activo, providers={sess.get_providers()}",
              file=sys.stderr)
        sys.exit(1)

    inp = sess.get_inputs()[0]
    c = inp.shape[1] if isinstance(inp.shape[1], int) else 1
    h = inp.shape[2] if isinstance(inp.shape[2], int) else 224
    w = inp.shape[3] if isinstance(inp.shape[3], int) else 224

    feed = {inp.name: np.random.rand(1, c, h, w).astype(np.float32)}

    # Calienta una vez para compilar kernels
    sess.run(None, feed)

    sys.stdout.write("dGPU_STRESS_READY\n")
    sys.stdout.flush()

    while not STOP:
        sess.run(None, feed)


if __name__ == "__main__":
    main()
