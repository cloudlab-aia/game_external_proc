#!/usr/bin/env python3
"""
benchmark_standalone.py

Benchmark de inferencia desacoplado del wrapper SHM.
Carga o genera una imagen de entrada y la pasa directamente al modelo
seleccionado en el dispositivo solicitado, midiendo latencia pura de inferencia.

Dispositivos soportados (los 6 del TFG, sin NPU):
    CPU_OCV      - OpenCV DNN, target CPU          (modelos .pb)
    CPU_OV       - OpenVINO, device "CPU"          (modelos .onnx y .xml)
    iGPU_OCL     - OpenCV DNN, target OpenCL Intel (modelos .pb)
    iGPU_OV      - OpenVINO, device "GPU"          (modelos .onnx y .xml)
    dGPU_CUDA    - ONNX Runtime, CUDAExecutionProvider (modelos .onnx)
    dGPU_OCL     - OpenCV DNN, target OpenCL NVIDIA (modelos .pb)

Escribe una fila al CSV de resultados por ejecucion.
Con --save_outputs guarda imagen de comparacion (input / bicubico / modelo).
"""

import argparse
import csv
import os
import sys
import time
import numpy as np

SUPPORTED_DEVICES = [
    "CPU_OCV", "CPU_OV", "iGPU_OCL", "iGPU_OV", "dGPU_CUDA", "dGPU_OCL",
]


# ─────────────────────────────────────────────────────────────────────────────
# Carga / generacion de imagen de entrada
# ─────────────────────────────────────────────────────────────────────────────

def load_input_image(image_path, w, h):
    """Carga imagen de disco y redimensiona a w×h (BGR, uint8)."""
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")
    if img.shape[1] != w or img.shape[0] != h:
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4)
    return img


def make_test_frame(w, h, scene_type="mixed", seed=42):
    """Genera frame estructurado tipo-juego (no ruido aleatorio)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    try:
        from phase2.generate_test_frames import generate_frame
        return generate_frame(w, h, scene_type, seed=seed)  # devuelve BGR
    except ImportError:
        # Fallback: checkerboard simple
        import cv2
        cell = max(8, min(w, h) // 16)
        xs = np.arange(w) // cell
        ys = np.arange(h) // cell
        grid = ((xs[np.newaxis, :] + ys[:, np.newaxis]) % 2).astype(np.uint8)
        img = np.where(grid[:, :, np.newaxis],
                       np.array([215, 215, 215], dtype=np.uint8),
                       np.array([40, 40, 40], dtype=np.uint8))
        return img.astype(np.uint8)


def get_input_image(args, w, h):
    """Devuelve imagen BGR uint8 de tamaño w×h según argumentos."""
    if args.image:
        return load_input_image(args.image, w, h)
    return make_test_frame(w, h, scene_type=args.scene_type, seed=42)


def percentile_stats(a):
    a = np.asarray(a, dtype=np.float64)
    return {
        "mean": float(a.mean()),
        "std":  float(a.std()),
        "p50":  float(np.percentile(a, 50)),
        "p90":  float(np.percentile(a, 90)),
        "p99":  float(np.percentile(a, 99)),
        "min":  float(a.min()),
        "max":  float(a.max()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Metricas de calidad
# ─────────────────────────────────────────────────────────────────────────────

def psnr(ref, out):
    """PSNR en dB entre dos imágenes BGR uint8."""
    ref_f = ref.astype(np.float64)
    out_f = out.astype(np.float64)
    mse = np.mean((ref_f - out_f) ** 2)
    if mse == 0:
        return float("inf")
    return float(20 * np.log10(255.0) - 10 * np.log10(mse))


def ssim_simple(ref, out):
    """SSIM simplificado (media por canal) sobre imágenes BGR uint8."""
    import cv2
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    scores = []
    for c in range(ref.shape[2]):
        r = ref[:, :, c].astype(np.float64)
        o = out[:, :, c].astype(np.float64)
        mu_r = cv2.GaussianBlur(r, (11, 11), 1.5)
        mu_o = cv2.GaussianBlur(o, (11, 11), 1.5)
        sr = cv2.GaussianBlur(r * r, (11, 11), 1.5) - mu_r ** 2
        so = cv2.GaussianBlur(o * o, (11, 11), 1.5) - mu_o ** 2
        sro = cv2.GaussianBlur(r * o, (11, 11), 1.5) - mu_r * mu_o
        num = (2 * mu_r * mu_o + C1) * (2 * sro + C2)
        den = (mu_r ** 2 + mu_o ** 2 + C1) * (sr + so + C2)
        scores.append(float(np.mean(num / den)))
    return float(np.mean(scores))


def quality_metrics(input_bgr, output_bgr):
    """Devuelve (psnr_vs_bicubic, ssim_vs_bicubic) comparando modelo vs bicubico."""
    import cv2
    oh, ow = output_bgr.shape[:2]
    bicubic = cv2.resize(input_bgr, (ow, oh), interpolation=cv2.INTER_CUBIC)
    return round(psnr(bicubic, output_bgr), 4), round(ssim_simple(bicubic, output_bgr), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Guardado de imagen comparativa
# ─────────────────────────────────────────────────────────────────────────────

def save_comparison(input_bgr, output_bgr, out_path):
    """Guarda tira horizontal: input | salida modelo."""
    import cv2
    oh, ow = output_bgr.shape[:2]
    inp_up = cv2.resize(input_bgr, (ow, oh), interpolation=cv2.INTER_NEAREST)

    def label(img, text):
        out = img.copy()
        cv2.putText(out, text, (6, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 1, cv2.LINE_AA)
        return out

    strip = np.concatenate([
        label(inp_up,  "INPUT"),
        label(output_bgr, "OUTPUT"),
    ], axis=1)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, strip)


# ─────────────────────────────────────────────────────────────────────────────
# Backends de inferencia
# ─────────────────────────────────────────────────────────────────────────────

def run_opencv_dnn(model_path, device, img_bgr, warmup, iters):
    import cv2
    from cv2 import dnn_superres

    base = os.path.basename(model_path).upper()
    if "FSRCNN" in base:
        scale = int(base.split("_X")[-1].split(".")[0])
        kind = "fsrcnn"
    elif "EDSR" in base:
        scale = int(base.split("_X")[-1].split(".")[0])
        kind = "edsr"
    elif "LAPSRN" in base:
        scale = int(base.split("_X")[-1].split(".")[0])
        kind = "lapsrn"
    else:
        raise ValueError(f"Tipo .pb no reconocido: {base}")

    sr = dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model_path)
    sr.setModel(kind, scale)
    sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)

    if device == "CPU_OCV":
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    elif device in ("iGPU_OCL", "dGPU_OCL"):
        cv2.ocl.setUseOpenCL(True)
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
    else:
        raise ValueError(f"Device {device} no soportado por OpenCV DNN")

    d = cv2.ocl.Device_getDefault() if device in ("iGPU_OCL", "dGPU_OCL") else None
    active_device_name = d.name() if d else "CPU"

    for _ in range(warmup):
        sr.upsample(img_bgr)

    lat = []
    out = None
    for _ in range(iters):
        t0 = time.perf_counter()
        out = sr.upsample(img_bgr)
        lat.append((time.perf_counter() - t0) * 1000.0)

    return lat, active_device_name, (out.shape[1], out.shape[0]), (kind, scale), out


def run_openvino(model_path, device, img_bgr, input_w, input_h, warmup, iters):
    import cv2
    import openvino as ov

    core = ov.Core()
    ov_device = "CPU" if device == "CPU_OV" else "GPU"
    model = core.read_model(model_path)

    inputs = model.inputs
    if len(inputs) == 1:
        inp = inputs[0]
        # Detecta layout: FSRCNN convertido desde TF .pb usa NHWC.
        # Modelos precompilados (super-resolution-10, etc.) usan NCHW.
        is_nhwc = "FSRCNN" in os.path.basename(model_path).upper()
        if inp.partial_shape[1].is_static:
            c = inp.partial_shape[1].get_length()
        else:
            c = 1
        try:
            if is_nhwc:
                # FSRCNN: 1 canal (Y de YCrCb), layout NHWC
                model.reshape({inp.any_name: [1, input_h, input_w, 1]})
                c = 1
            else:
                model.reshape({inp.any_name: [1, c, input_h, input_w]})
        except Exception as e:
            print(f"[WARN] reshape failed ({e}), using original shape", file=sys.stderr)
        compiled = core.compile_model(model, ov_device)
        req = compiled.create_infer_request()

        if is_nhwc:
            ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
            y = ycc[:, :, 0].astype(np.float32) / 255.0
            feed = {inp.any_name: y[None, :, :, None]}
        elif c == 1:
            ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
            y = ycc[:, :, 0].astype(np.float32) / 255.0
            feed = {inp.any_name: y[None, None, :, :]}
        else:
            arr = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            feed = {inp.any_name: arr.transpose(2, 0, 1)[None, :, :, :]}

        for _ in range(warmup):
            req.infer(feed)
        lat = []
        raw_out = None
        for _ in range(iters):
            t0 = time.perf_counter()
            raw_out = req.infer(feed)
            lat.append((time.perf_counter() - t0) * 1000.0)

        first = next(iter(raw_out.values()))
        if is_nhwc:
            # NHWC: shape=[N,H,W,C] → out_w=shape[-2], out_h=shape[-3]
            out_shape = (int(first.shape[-2]), int(first.shape[-3]))
        else:
            out_shape = (int(first.shape[-1]), int(first.shape[-2]))

        # Reconstruye imagen BGR para comparativa
        out_arr = np.squeeze(first)
        if c == 1:
            out_y = np.clip(out_arr * 255.0, 0, 255).astype(np.uint8)
            # Upscale de Cb/Cr por bicubic y recompone YCrCb
            out_h_img, out_w_img = out_y.shape
            cb = cv2.resize(ycc[:, :, 1], (out_w_img, out_h_img), interpolation=cv2.INTER_CUBIC)
            cr = cv2.resize(ycc[:, :, 2], (out_w_img, out_h_img), interpolation=cv2.INTER_CUBIC)
            ycc_out = np.stack([out_y, cb, cr], axis=2)
            out_bgr = cv2.cvtColor(ycc_out, cv2.COLOR_YCrCb2BGR)
        else:
            out_rgb = np.clip(out_arr.transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)
            out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

        kind = os.path.basename(model_path)
        return lat, f"OV:{ov_device}", out_shape, (kind, None), out_bgr
    else:
        # single-image-super-resolution-1032: 2 entradas con shape estático.
        # input0 = LR (h_lr, w_lr), input1 = bicubic HR (h_lr*4, w_lr*4).
        compiled = core.compile_model(model, ov_device)
        req = compiled.create_infer_request()

        # Determina LR (entrada más pequeña) y HR (más grande)
        shapes = []
        for i in inputs:
            s = [d.get_length() if d.is_static else 1 for d in i.partial_shape]
            shapes.append((s[-2] * s[-1], s[-2], s[-1], i.any_name))
        shapes.sort()  # menor a mayor area
        _, h_lr, w_lr, name_lr = shapes[0]
        _, h_hr, w_hr, name_hr = shapes[1]

        # Imagen LR: redimensiona al tamaño de entrada del modelo
        lr_bgr  = cv2.resize(img_bgr, (w_lr, h_lr), interpolation=cv2.INTER_LANCZOS4)
        hr_bgr  = cv2.resize(lr_bgr,  (w_hr, h_hr), interpolation=cv2.INTER_CUBIC)

        def bgr_to_nchw(img):
            arr = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            return arr.transpose(2, 0, 1)[None, :, :, :].astype(np.float32)

        feed = {name_lr: bgr_to_nchw(lr_bgr), name_hr: bgr_to_nchw(hr_bgr)}
        # img_bgr eficaz para métricas = la LR que se pasó al modelo
        img_bgr = lr_bgr

        for _ in range(warmup):
            req.infer(feed)
        lat = []
        raw_out = None
        for _ in range(iters):
            t0 = time.perf_counter()
            raw_out = req.infer(feed)
            lat.append((time.perf_counter() - t0) * 1000.0)

        first = next(iter(raw_out.values()))
        out_shape = (int(first.shape[-1]), int(first.shape[-2]))
        # Modelo de aprendizaje residual: output = bicubic_hr + residual
        residual = np.squeeze(first)       # (C, H, W) float32
        bic_nchw = bgr_to_nchw(hr_bgr)[0] # (C, H, W) float32, ya en [0,1]
        final = np.clip(bic_nchw + residual, 0.0, 1.0)
        out_rgb = (final.transpose(1, 2, 0) * 255.0).astype(np.uint8)
        out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)
        return lat, f"OV:{ov_device}", out_shape, (os.path.basename(model_path), None), out_bgr


def run_onnxruntime_cuda(model_path, img_bgr, input_w, input_h, warmup, iters):
    import cv2
    import onnxruntime as ort
    sess_opts = ort.SessionOptions()
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    sess = ort.InferenceSession(model_path, sess_opts, providers=providers)
    active = sess.get_providers()
    if "CUDAExecutionProvider" not in active:
        raise RuntimeError(f"CUDA provider no activo: {active}")

    inp = sess.get_inputs()[0]
    c = inp.shape[1] if (len(inp.shape) >= 2 and isinstance(inp.shape[1], int)) else 3

    if c == 1:
        ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        y = ycc[:, :, 0].astype(np.float32) / 255.0
        feed = {inp.name: y[None, None, :, :]}
    else:
        arr = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        feed = {inp.name: arr.transpose(2, 0, 1)[None, :, :, :]}

    for _ in range(warmup):
        sess.run(None, feed)
    lat = []
    raw_out = None
    for _ in range(iters):
        t0 = time.perf_counter()
        raw_out = sess.run(None, feed)
        lat.append((time.perf_counter() - t0) * 1000.0)

    out_shape = (int(raw_out[0].shape[-1]), int(raw_out[0].shape[-2]))
    out_arr = np.squeeze(raw_out[0])
    if c == 1:
        out_y = np.clip(out_arr * 255.0, 0, 255).astype(np.uint8)
        out_h_img, out_w_img = out_y.shape
        cb = cv2.resize(ycc[:, :, 1], (out_w_img, out_h_img), interpolation=cv2.INTER_CUBIC)
        cr = cv2.resize(ycc[:, :, 2], (out_w_img, out_h_img), interpolation=cv2.INTER_CUBIC)
        ycc_out = np.stack([out_y, cb, cr], axis=2)
        out_bgr = cv2.cvtColor(ycc_out, cv2.COLOR_YCrCb2BGR)
    else:
        out_rgb = np.clip(out_arr.transpose(1, 2, 0) * 255.0, 0, 255).astype(np.uint8)
        out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

    return lat, "CUDA:RTX5060", out_shape, (os.path.basename(model_path), None), out_bgr


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", required=True, choices=SUPPORTED_DEVICES)
    parser.add_argument("--input_size", nargs=2, type=int, default=[320, 240])
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--load_tag", default="idle")
    parser.add_argument("--out_csv", default="viability/results/viability_results.csv")
    parser.add_argument("--run_id", default="")
    # Imagen de entrada
    parser.add_argument("--image", default=None,
                        help="Ruta a imagen real de entrada. Si no se indica, "
                             "se genera un frame de test estructurado.")
    parser.add_argument("--scene_type", default="mixed",
                        choices=["gradient", "checkerboard", "edges", "mixed"],
                        help="Tipo de frame de test si no se provee --image")
    # Outputs visuales
    parser.add_argument("--save_outputs", action="store_true",
                        help="Guarda imagen comparativa input/bicubico/modelo")
    parser.add_argument("--out_images_dir",
                        default="viability/results/sample_outputs")
    args = parser.parse_args()

    input_w, input_h = args.input_size
    device = args.device
    model_path = args.model
    model_name = os.path.basename(model_path)

    img_bgr = get_input_image(args, input_w, input_h)

    try:
        if device in ("CPU_OCV", "iGPU_OCL", "dGPU_OCL"):
            if not model_path.endswith(".pb"):
                print(f"[SKIP] {device} requiere modelo .pb, recibido {model_name}")
                return 2
            t_start = time.perf_counter()
            lat, active_dev, out_shape, meta, out_bgr = run_opencv_dnn(
                model_path, device, img_bgr, args.warmup, args.iters
            )
            wall = time.perf_counter() - t_start
        elif device in ("CPU_OV", "iGPU_OV"):
            if not (model_path.endswith(".onnx") or model_path.endswith(".xml")):
                print(f"[SKIP] {device} requiere .onnx o .xml, recibido {model_name}")
                return 2
            t_start = time.perf_counter()
            lat, active_dev, out_shape, meta, out_bgr = run_openvino(
                model_path, device, img_bgr, input_w, input_h, args.warmup, args.iters
            )
            wall = time.perf_counter() - t_start
        elif device == "dGPU_CUDA":
            if not model_path.endswith(".onnx"):
                print(f"[SKIP] {device} requiere .onnx, recibido {model_name}")
                return 2
            t_start = time.perf_counter()
            lat, active_dev, out_shape, meta, out_bgr = run_onnxruntime_cuda(
                model_path, img_bgr, input_w, input_h, args.warmup, args.iters
            )
            wall = time.perf_counter() - t_start
        else:
            print(f"[!] Dispositivo no soportado: {device}")
            return 2
    except Exception as e:
        print(f"[ERROR] {device} {model_name} {input_w}x{input_h}: {e}")
        return 1

    s = percentile_stats(lat)
    fps_p50 = 1000.0 / s["p50"] if s["p50"] > 0 else 0.0
    fps_mean = 1000.0 / s["mean"] if s["mean"] > 0 else 0.0

    # Métricas de calidad
    psnr_val, ssim_val = quality_metrics(img_bgr, out_bgr)

    # Imagen comparativa
    if args.save_outputs:
        tag = f"{model_name.replace('.','_')}_{device}_{input_w}x{input_h}_{args.load_tag}"
        img_out_path = os.path.join(args.out_images_dir, f"{tag}.png")
        save_comparison(img_bgr, out_bgr, img_out_path)

    print(f"[OK] {device:10s} {model_name:30s} {input_w}x{input_h:4d} load={args.load_tag:6s} "
          f"mean={s['mean']:7.2f} p50={s['p50']:7.2f} p90={s['p90']:7.2f} p99={s['p99']:7.2f} "
          f"FPS(p50)={fps_p50:6.1f} PSNR={psnr_val:5.2f} SSIM={ssim_val:.4f} active={active_dev}")

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    header = [
        "run_id", "timestamp", "device", "model", "input_w", "input_h",
        "output_w", "output_h", "load_tag",
        "warmup", "iters", "wall_s",
        "mean_ms", "std_ms", "p50_ms", "p90_ms", "p99_ms", "min_ms", "max_ms",
        "fps_mean", "fps_p50", "active_backend_name",
        "psnr_vs_bicubic", "ssim_vs_bicubic",
        "image_source",
    ]
    write_header = not os.path.isfile(args.out_csv)
    with open(args.out_csv, "a", newline="") as cf:
        w = csv.writer(cf)
        if write_header:
            w.writerow(header)
        w.writerow([
            args.run_id or time.strftime("%Y%m%dT%H%M%S"),
            time.strftime("%Y-%m-%dT%H:%M:%S"),
            device, model_name, input_w, input_h,
            out_shape[0], out_shape[1], args.load_tag,
            args.warmup, args.iters, round(wall, 3),
            round(s["mean"], 3), round(s["std"], 3),
            round(s["p50"], 3), round(s["p90"], 3), round(s["p99"], 3),
            round(s["min"], 3), round(s["max"], 3),
            round(fps_mean, 2), round(fps_p50, 2),
            active_dev,
            psnr_val, ssim_val,
            os.path.basename(args.image) if args.image else f"synth:{args.scene_type}",
        ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
