#!/usr/bin/env python3
"""
benchmark_models.py
Mejorado: warm-up, pre/infer/post timings, ONNXRuntime fallback para .onnx, guardado imagen de ejemplo,
header handshake (width,height,seq,ready) esperado en shm.
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

MODELS_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models"
SHM_PATH = "/dev/shm/framebuffer_shared"  # POSIX shm file visible en /dev/shm/
HEADER_FMT = "IIII"   # width, height, seq, ready
HEADER_SIZE = struct.calcsize(HEADER_FMT)

def read_shm_header(f):
    f.seek(0)
    h = f.read(HEADER_SIZE)
    if len(h) < HEADER_SIZE:
        return None
    return struct.unpack(HEADER_FMT, h)  # (w,h,seq,ready)

def read_frame_raw(f, width, height):
    frame_size = width * height * 4
    f.seek(HEADER_SIZE)
    frame = f.read(frame_size)
    if len(frame) < frame_size:
        return None
    arr = np.frombuffer(frame, dtype=np.uint8).reshape((height, width, 4))
    return arr

def wait_for_frame(expected_w, expected_h, timeout=5.0, last_seq=0):
    start = time.time()
    with open(SHM_PATH, "rb") as f:
        while time.time() - start < timeout:
            hdr = read_shm_header(f)
            if not hdr:
                time.sleep(0.05)
                continue
            w,h,seq,ready = hdr
            if ready != 1 or seq == last_seq:
                time.sleep(0.02)
                continue
            if w == expected_w and h == expected_h:
                frame = read_frame_raw(f, w, h)
                if frame is None:
                    time.sleep(0.02)
                    continue
                # Convert RGBA->RGB and flip already performed by writer (should be top-down)
                rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                return rgb, seq
            else:
                # return the frame anyway so caller can resize if desired
                frame = read_frame_raw(f, w, h)
                if frame is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                    return rgb, seq
            time.sleep(0.02)
    return None, None

def load_model_cv2(sr, model_path):
    if model_path.endswith(".pb"):
        # FSRCNN ... EDSR ... etc
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
            # fallback
            sr.readModel(model_path)
            return (None, None)
    else:
        raise ValueError("Formato no soportado por load_model_cv2")

def run_onnx_inference(sess, input_image, input_name, preproc_cfg=None):
    # input_image: HxWx3 uint8 (RGB)
    # preproc_cfg: dict with 'scale' and 'mean' optionally
    img = input_image.astype(np.float32)
    # Default: normalize to 0..1
    img = img / 255.0
    # Convert to NCHW
    img = img.transpose(2,0,1)[None, :, :, :].astype(np.float32)
    ort_inputs = {input_name: img}
    out = sess.run(None, ort_inputs)
    # Attempt to recover HxWx3 from output (assume single output and CHW)
    out0 = out[0]
    if isinstance(out0, list):
        out0 = out0[0]
    # out0 shape: N,C,H,W
    if out0.ndim == 4:
        out0 = out0[0].transpose(1,2,0)
    return np.clip(out0 * 255.0, 0, 255).astype(np.uint8)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--input_size", nargs=2, type=int, required=True)
    parser.add_argument("--output_size", nargs=2, type=int, required=True)
    parser.add_argument("--device", choices=["cpu","opencl","npu"], default="cpu")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--save_example", action="store_true")
    args = parser.parse_args()

    input_w, input_h = args.input_size
    output_w, output_h = args.output_size

    model_path = args.model
    model_name = os.path.basename(model_path)

    sr = dnn_superres.DnnSuperResImpl_create()
    onnx_sess = None
    onnx_input_name = None
    model_kind = None
    model_scale = None

    # Try load via cv2 dnn_superres if .pb otherwise try onnxruntime
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
            use_cv2 = False
    elif model_path.endswith(".onnx"):
        if not ONNX_AVAILABLE:
            print("[!] onnxruntime no disponible. Instala onnxruntime para usar .onnx")
            return
        try:
            # create session
            providers = ["CPUExecutionProvider"]
            # try to use CUDA if available in ort
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers = ["CUDAExecutionProvider","CPUExecutionProvider"]
            onnx_sess = ort.InferenceSession(model_path, providers=providers)
            onnx_input_name = onnx_sess.get_inputs()[0].name
            use_cv2 = False
        except Exception as e:
            print(f"[!] Error creando ONNX session: {e}")
            return
    else:
        print("[!] Modelo no soportado (solo .pb o .onnx)")
        return

    print(f"[*] Model: {model_name}, device={args.device}, input={input_w}x{input_h}, output={output_w}x{output_h}")

    # Warmup: wait for a frame and run warmup times without measuring
    last_seq = 0
    print(f"[*] Esperando primer frame y haciendo {args.warmup} warm-up inferences...")
    for i in range(args.warmup):
        frame, seq = wait_for_frame(input_w, input_h, timeout=5.0, last_seq=last_seq)
        if frame is None:
            print("    [!] No frame in warmup")
            continue
        last_seq = seq
        img = frame
        # Resize to input size if necessary
        if img.shape[1] != input_w or img.shape[0] != input_h:
            img = cv2.resize(img, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        try:
            if use_cv2:
                _ = sr.upsample(img)
            else:
                _ = run_onnx_inference(onnx_sess, img, onnx_input_name)
        except Exception as e:
            print(f"    [!] Warmup error: {e}")

    times_total = []
    times_pre = []
    times_infer = []
    times_post = []
    frames_ok = 0

    example_saved = False
    example_dir = "benchmark_examples"
    os.makedirs(example_dir, exist_ok=True)

    for i in range(args.iters):
        frame, seq = wait_for_frame(input_w, input_h, timeout=6.0, last_seq=last_seq)
        if frame is None:
            print(f"    [!] iter {i}: no frame disponible")
            continue
        last_seq = seq
        img = frame
        # preproc timing (resize to model input)
        t0 = time.time()
        if img.shape[1] != input_w or img.shape[0] != input_h:
            pre_img = cv2.resize(img, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
        else:
            pre_img = img
        t1 = time.time()

        # inference
        try:
            if use_cv2:
                t_in_start = time.time()
                out = sr.upsample(pre_img)
                t_in_end = time.time()
            else:
                t_in_start = time.time()
                out = run_onnx_inference(onnx_sess, pre_img, onnx_input_name)
                t_in_end = time.time()
        except Exception as e:
            print(f"    [!] Error durante inferencia: {e}")
            continue

        # postproc: resize to output_w/output_h if needed
        t_post_start = time.time()
        if out.shape[1] != output_w or out.shape[0] != output_h:
            out_resized = cv2.resize(out, (output_w, output_h), interpolation=cv2.INTER_LINEAR)
        else:
            out_resized = out
        t_post_end = time.time()

        pre_ms = (t1 - t0) * 1000.0
        infer_ms = (t_in_end - t_in_start) * 1000.0
        post_ms = (t_post_end - t_post_start) * 1000.0
        total_ms = pre_ms + infer_ms + post_ms

        times_total.append(total_ms)
        times_pre.append(pre_ms)
        times_infer.append(infer_ms)
        times_post.append(post_ms)
        frames_ok += 1

        # guardar ejemplo (primer resultado)
        if args.save_example and not example_saved:
            fn = os.path.join(example_dir, f"{model_name}_{args.device}_{input_w}x{input_h}.png")
            cv2.imwrite(fn, cv2.cvtColor(out_resized, cv2.COLOR_RGB2BGR))
            example_saved = True

    if frames_ok == 0:
        print("    -> No frames procesados")
        return

    # estadísticas
    arr_total = np.array(times_total)
    arr_pre = np.array(times_pre)
    arr_inf = np.array(times_infer)
    arr_post = np.array(times_post)

    def stats(a):
        return {
            "mean": float(np.mean(a)),
            "std": float(np.std(a)),
            "p50": float(np.percentile(a,50)),
            "p90": float(np.percentile(a,90)),
            "p99": float(np.percentile(a,99)),
        }

    s_total = stats(arr_total)
    s_pre = stats(arr_pre)
    s_inf = stats(arr_inf)
    s_post = stats(arr_post)

    # print summary
    print("RESULT SUMMARY:")
    print(f" frames: {frames_ok}")
    print(f" total ms mean/std/p50/p90/p99: {s_total['mean']:.2f}/{s_total['std']:.2f}/{s_total['p50']:.2f}/{s_total['p90']:.2f}/{s_total['p99']:.2f}")
    print(f" infer ms mean/p90: {s_inf['mean']:.2f}/{s_inf['p90']:.2f}")

    # Append to CSV
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
            os.path.basename(model_path),
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
