"""Mide la latencia de inferencia de FSRCNN en un dispositivo, a una resolución
de entrada y un factor de escala dados, opcionalmente bajo carga.

Dispositivos:
  iGPU  -> OpenVINO, device GPU (Intel), modelo IR (models/openvino_ir/FSRCNN_x{s}.xml)
  CPU   -> OpenVINO, device CPU,          modelo IR
  dGPU  -> ONNX Runtime, CUDAExecutionProvider (NVIDIA), modelo ONNX (models/FSRCNN_x{s}.onnx)

FSRCNN opera sobre el canal Y (1 canal), entrada NHWC [1,H,W,1]. Se mide con
entrada sintética: la latencia de inferencia no depende del contenido.

Escribe una fila a un CSV. Pensado para llamarse desde los orquestadores de
experimentos (run_expA.sh, run_expB.sh).

Uso:
  python3 experiments/bench_inference.py --device iGPU --scale 4 \
      --in_w 480 --in_h 270 --warmup 5 --iters 50 --load_tag idle \
      --out_csv results/experiments/expA.csv
"""
import argparse
import csv
import os
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bench_openvino(ir_path, ov_device, ih, iw, warmup, iters):
    import openvino as ov
    core = ov.Core()
    m = core.read_model(ir_path)
    m.reshape([1, ih, iw, 1])
    req = core.compile_model(m, ov_device, {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()
    x = np.random.rand(1, ih, iw, 1).astype(np.float32)
    for _ in range(warmup):
        req.infer({0: x})
    lat = []
    for _ in range(iters):
        t = time.perf_counter_ns()
        req.infer({0: x})
        lat.append((time.perf_counter_ns() - t) / 1e6)
    return lat, "OV:" + ov_device


def bench_onnx_cuda(onnx_path, ih, iw, warmup, iters):
    import onnxruntime as ort
    ort.preload_dlls()
    s = ort.InferenceSession(onnx_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    active = s.get_providers()[0]
    if active != "CUDAExecutionProvider":
        raise RuntimeError(f"CUDA no activo (provider={active})")
    name = s.get_inputs()[0].name
    x = np.random.rand(1, ih, iw, 1).astype(np.float32)
    for _ in range(warmup):
        s.run(None, {name: x})
    lat = []
    for _ in range(iters):
        t = time.perf_counter_ns()
        s.run(None, {name: x})
        lat.append((time.perf_counter_ns() - t) / 1e6)
    return lat, "ORT:CUDA"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True, choices=["iGPU", "CPU", "dGPU"])
    ap.add_argument("--scale", type=int, required=True, choices=[2, 3, 4])
    ap.add_argument("--in_w", type=int, required=True)
    ap.add_argument("--in_h", type=int, required=True)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--load_tag", default="idle")
    ap.add_argument("--out_csv", required=True)
    args = ap.parse_args()

    ir = os.path.join(REPO, "models", "openvino_ir", f"FSRCNN_x{args.scale}.xml")
    onnx = os.path.join(REPO, "models", f"FSRCNN_x{args.scale}.onnx")

    try:
        if args.device == "iGPU":
            lat, backend = bench_openvino(ir, "GPU", args.in_h, args.in_w, args.warmup, args.iters)
        elif args.device == "CPU":
            lat, backend = bench_openvino(ir, "CPU", args.in_h, args.in_w, args.warmup, args.iters)
        else:
            lat, backend = bench_onnx_cuda(onnx, args.in_h, args.in_w, args.warmup, args.iters)
    except Exception as e:
        print(f"[ERROR] {args.device} x{args.scale} {args.in_w}x{args.in_h} {args.load_tag}: {repr(e)[:150]}")
        return

    a = np.array(lat)
    row = {
        "device": args.device, "backend": backend, "scale": args.scale,
        "in_w": args.in_w, "in_h": args.in_h,
        "out_w": args.in_w * args.scale, "out_h": args.in_h * args.scale,
        "load_tag": args.load_tag, "iters": args.iters,
        "mean_ms": round(a.mean(), 3), "p50_ms": round(np.percentile(a, 50), 3),
        "p95_ms": round(np.percentile(a, 95), 3), "fps_p50": round(1000 / np.percentile(a, 50), 1),
    }
    new = not os.path.exists(args.out_csv)
    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    with open(args.out_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"[OK] {args.device:5} x{args.scale} {args.in_w}x{args.in_h} load={args.load_tag:5} "
          f"-> p50={row['p50_ms']:.2f}ms ({row['fps_p50']:.0f} FPS) [{backend}]")


if __name__ == "__main__":
    main()
