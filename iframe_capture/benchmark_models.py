#!/usr/bin/env python3
"""
benchmark_models.py
Versión lista para funcionar con wrapper_swapbuffers_shm.c
Lee frames desde /dev/shm/framebuffer_shared, redimensiona y aplica modelos de superresolución.
"""

import cv2
import time
import numpy as np
import os
import argparse
from cv2 import dnn_superres
import csv
import struct
import sys

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except Exception:
    ONNX_AVAILABLE = False

# Paths
SHM_PATH = "/dev/shm/framebuffer_shared"
HEADER_FMT = "IIII"   # width, height, seq, ready
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# ---- Funciones de lectura ----
def read_shm_header(f):
    f.seek(0)
    h = f.read(HEADER_SIZE)
    if len(h) < HEADER_SIZE:
        return None
    return struct.unpack(HEADER_FMT, h)  # w,h,seq,ready

def read_frame_raw(f, width, height):
    frame_size = width * height * 4
    f.seek(HEADER_SIZE)
    frame = f.read(frame_size)
    if len(frame) < frame_size:
        return None
    arr = np.frombuffer(frame, dtype=np.uint8).reshape((height, width, 4))
    return arr

def wait_for_frame(expected_w, expected_h, timeout=5.0, last_seq=0, debug=False):
    start = time.time()
    with open(SHM_PATH, "rb") as f:
        while time.time() - start < timeout:
            hdr = read_shm_header(f)
            if not hdr:
                time.sleep(0.05)
                continue
            w,h,seq,ready = hdr
            if debug:
                print(f"[DEBUG] Header: w={w}, h={h}, seq={seq}, ready={ready}")
            if ready != 1 or seq == last_seq:
                time.sleep(0.02)
                continue
            frame = read_frame_raw(f, w, h)
            if frame is None:
                time.sleep(0.02)
                continue
            # Convert RGBA -> RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
            last_seq = seq
            # Redimensionar al tamaño esperado por el modelo
            if w != expected_w or h != expected_h:
                rgb = cv2.resize(rgb, (expected_w, expected_h), interpolation=cv2.INTER_LINEAR)
            return rgb, seq
    return None, None

# ---- Funciones para cargar modelos ----
def load_model_cv2(sr, model_path):
    if model_path.endswith(".pb"):
        base = os.path.basename(model_path).upper()
        if "FSRCNN" in base:
            scale = int(base.split("_X")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("fsrcnn", scale)
            return ("fsrcnn", scale)
        elif "EDSR" in base:
            scale = int(base.split("_X")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("edsr", scale)
            return ("edsr", scale)
        elif "LAPSRN" in base:
            scale = int(base.split("_X")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("lapsrn", scale)
            return ("lapsrn", scale)
        else:
            sr.readModel(model_path)
            return (None, None)
    else:
        raise ValueError("Formato no soportado por load_model_cv2")

def run_onnx_inference(sess, input_image, input_name):
    img = input_image.astype(np.float32) / 255.0
    img = img.transpose(2,0,1)[None,:,:,:].astype(np.float32)  # NCHW
    ort_inputs = {input_name: img}
    out = sess.run(None, ort_inputs)
    out0 = out[0]
    if out0.ndim == 4:
        out0 = out0[0].transpose(1,2,0)
    return np.clip(out0 * 255.0, 0, 255).astype(np.uint8)

# ---- Main ----
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input_size", nargs=2, type=int, required=True)
    parser.add_argument("--output_size", nargs=2, type=int, required=True)
    parser.add_argument("--device", choices=["cpu","opencl","npu"], default="cpu")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--save_example", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    input_w, input_h = args.input_size
    output_w, output_h = args.output_size
    model_path = args.model
    model_name = os.path.basename(model_path)

    sr = dnn_superres.DnnSuperResImpl_create()
    onnx_sess = None
    onnx_input_name = None
    use_cv2 = False

    if model_path.endswith(".pb"):
        try:
            model_kind, model_scale = load_model_cv2(sr, model_path)
            sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            if args.device == "cpu":
                sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            elif args.device == "opencl":
                sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
            else:
                print("[!] NPU no soportado por cv2.dnn_superres. Salimos.")
                return
            use_cv2 = True
        except Exception as e:
            print(f"[!] Error cargando modelo .pb con cv2: {e}")
            return
    elif model_path.endswith(".onnx"):
        if not ONNX_AVAILABLE:
            print("[!] onnxruntime no disponible")
            return
        try:
            providers = ["CPUExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers = ["CUDAExecutionProvider","CPUExecutionProvider"]
            onnx_sess = ort.InferenceSession(model_path, providers=providers)
            onnx_input_name = onnx_sess.get_inputs()[0].name
            use_cv2 = False
        except Exception as e:
            print(f"[!] Error creando ONNX session: {e}")
            return
    else:
        print("[!] Modelo no soportado")
        return

    print(f"[*] Model: {model_name}, device={args.device}, input={input_w}x{input_h}, output={output_w}x{output_h}")

    # Warmup
    last_seq = 0
    print(f"[*] Warmup ({args.warmup} frames)...")
    for i in range(args.warmup):
        frame, seq = wait_for_frame(input_w, input_h, last_seq=last_seq, debug=args.debug)
        if frame is None:
            print("    [!] No frame in warmup")
            continue
        last_seq = seq
        if use_cv2:
            _ = sr.upsample(frame)
        else:
            _ = run_onnx_inference(onnx_sess, frame, onnx_input_name)

    # Benchmark
    times_total, times_pre, times_infer, times_post = [], [], [], []
    frames_ok = 0

    example_saved = False
    example_dir = "benchmark_examples"
    os.makedirs(example_dir, exist_ok=True)

    for i in range(args.iters):
        frame, seq = wait_for_frame(input_w, input_h, last_seq=last_seq, debug=args.debug)
        if frame is None:
            print(f"    [!] iter {i}: no frame disponible")
            continue
        last_seq = seq

        # Preprocessing
        t0 = time.time()
        if frame.shape[1] != input_w or frame.shape[0] != input_h:
            pre_img = cv2.resize(frame, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        else:
            pre_img = frame
        t1 = time.time()

        # Inference
        try:
            t_in_start = time.time()
            if use_cv2:
                out = sr.upsample(pre_img)
            else:
                out = run_onnx_inference(onnx_sess, pre_img, onnx_input_name)
            t_in_end = time.time()
        except Exception as e:
            print(f"    [!] Error durante inferencia: {e}")
            continue

        # Postprocessing
        t_post_start = time.time()
        if out.shape[1] != output_w or out.shape[0] != output_h:
            out_resized = cv2.resize(out, (output_w, output_h), interpolation=cv2.INTER_LINEAR)
        else:
            out_resized = out
        t_post_end = time.time()

        frames_ok += 1
        times_total.append((t1-t0)+(t_in_end-t_in_start)+(t_post_end-t_post_start)*1000.0)
        times_pre.append((t1-t0)*1000.0)
        times_infer.append((t_in_end-t_in_start)*1000.0)
        times_post.append((t_post_end-t_post_start)*1000.0)

        # Guardar primer ejemplo
        if args.save_example and not example_saved:
            fn = os.path.join(example_dir, f"{model_name}_{args.device}_{input_w}x{input_h}.png")
            cv2.imwrite(fn, cv2.cvtColor(out_resized, cv2.COLOR_RGB2BGR))
            example_saved = True

    if frames_ok == 0:
        print("    -> No frames procesados")
        return

    # Estadísticas
    def stats(a):
        a = np.array(a)
        return {
            "mean": float(np.mean(a)),
            "std": float(np.std(a)),
            "p50": float(np.percentile(a,50)),
            "p90": float(np.percentile(a,90)),
            "p99": float(np.percentile(a,99)),
        }

    s_total = stats(times_total)
    s_pre = stats(times_pre)
    s_inf = stats(times_infer)
    s_post = stats(times_post)

    print("RESULT SUMMARY:")
    print(f" frames: {frames_ok}")
    print(f" total ms mean/std/p50/p90/p99: {s_total['mean']:.2f}/{s_total['std']:.2f}/{s_total['p50']:.2f}/{s_total['p90']:.2f}/{s_total['p99']:.2f}")
    print(f" infer ms mean/p90: {s_inf['mean']:.2f}/{s_inf['p90']:.2f}")

    # Guardar CSV
    csv_file = "benchmark_results.csv"
    header = ["model","device","input_w","input_h","output_w","output_h",
              "frames","total_mean_ms","total_std_ms","total_p50","total_p90","total_p99",
              "infer_mean_ms","infer_p90_ms","pre_mean_ms","post_mean_ms"]
    write_header = not os.path.isfile(csv_file)
    with open(csv_file, "a", newline="") as cf:
        writer = csv.writer(cf)
        if write_header:
            writer.writerow(header)
        writer.writerow([
            model_name,
            args.device,
            input_w,
            input_h,
            output_w,
            output_h,
            frames_ok,
            round(s_total['mean'],2),
            round(s_total['std'],2),
            round(s_total['p50'],2),
            round(s_total['p90'],2),
            round(s_total['p99'],2),
            round(s_inf['mean'],2),
            round(s_inf['p90'],2),
            round(s_pre['mean'],2),
            round(s_post['mean'],2),
        ])

if __name__ == "__main__":
    main()
