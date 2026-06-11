#!/usr/bin/env python3
"""
benchmark_models_shm.py

Lee frames desde /dev/shm/framebuffer_shared (header: width,u32 height,u32 seq,u32 ready,u32),
adapta automáticamente canales y tamaño a lo que espera el modelo (ONNX o .pb),
ejecuta warm-up + N iteraciones, mide pre/infer/post, guarda CSV y ejemplo.

Requisitos:
  pip3 install opencv-python opencv-contrib-python numpy onnxruntime
  (si no usas .onnx, onnxruntime no es obligatorio)
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

# Try import onnxruntime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except Exception:
    ONNX_AVAILABLE = False

SHM_PATH = "/dev/shm/framebuffer_shared"
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

def wait_for_frame(timeout=5.0, last_seq=0):
    """Espera hasta timeout por cualquier frame. Devuelve (frame_rgb, w, h, seq) o (None, None, None, None)."""
    start = time.time()
    try:
        with open(SHM_PATH, "rb") as f:
            while time.time() - start < timeout:
                hdr = read_shm_header(f)
                if not hdr:
                    time.sleep(0.02)
                    continue
                w,h,seq,ready = hdr
                if ready != 1 or seq == last_seq:
                    time.sleep(0.02)
                    continue
                frame = read_frame_raw(f, w, h)
                if frame is None:
                    time.sleep(0.02)
                    continue
                # frame is RGBA top-down (writer already flipped). Convert to RGB
                rgb = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                return rgb, w, h, seq
                # loop end
    except FileNotFoundError:
        return None, None, None, None
    return None, None, None, None

def onnx_input_info(sess):
    """Devuelve (channels, height, width) esperados por el input. None si dinámico."""
    inp = sess.get_inputs()[0]
    shape = inp.shape  # lista con elementos int or None
    # shape normalmente [N, C, H, W] pero puede variar
    if len(shape) >= 4:
        _, c, h, w = shape[:4]
        return (c, h, w)
    else:
        # fallback: intentar inferir por name/metadata
        return (None, None, None)

def prepare_input_for_onnx(img, want_c, want_h, want_w):
    """
    img: HxWx3 RGB (uint8) from shm or HxWx1 if preconverted.
    want_c: expected channels (1 or 3 or None)
    want_h/w: expected height/width (int or None)
    Devuelve tensor float32 NCHW normalized 0..1
    """
    src = img.copy()

    # If model expects grayscale (1), convert
    if want_c == 1:
        if src.ndim == 3:
            src = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)  # HxW
    else:
        # ensure RGB 3 channels
        if src.ndim == 2:
            src = cv2.cvtColor(src, cv2.COLOR_GRAY2RGB)

    # Resize if needed (if want_h/w not None)
    if want_h and want_w:
        src = cv2.resize(src, (want_w, want_h), interpolation=cv2.INTER_LINEAR)

    # Normalize to 0..1 float32
    arr = src.astype(np.float32) / 255.0

    # Make shape (N,C,H,W)
    if arr.ndim == 2:
        # single channel HxW -> 1x1xHxW
        arr = np.expand_dims(np.expand_dims(arr, axis=0), axis=0)
    else:
        # HxWx3 -> 1x3xHxW
        arr = arr.transpose(2,0,1)[None, :, :, :]

    return arr

def prepare_input_for_cv2_dnn(sr, img, model_kind, model_scale, input_w=None, input_h=None):
    """
    sr: cv2 DnnSuperResImpl instance already loaded.
    img: HxWx3 RGB uint8
    For cv2 dnn_superres we give it the HxW image and call sr.upsample.
    If the model expects a different input size, resize before calling.
    """
    src = img.copy()
    if input_w and input_h:
        if src.shape[1] != input_w or src.shape[0] != input_h:
            src = cv2.resize(src, (input_w, input_h), interpolation=cv2.INTER_LINEAR)
    return src

def stats_from_array(a):
    return {
        "mean": float(np.mean(a)) if len(a) else 0.0,
        "std": float(np.std(a)) if len(a) else 0.0,
        "p50": float(np.percentile(a,50)) if len(a) else 0.0,
        "p90": float(np.percentile(a,90)) if len(a) else 0.0,
        "p99": float(np.percentile(a,99)) if len(a) else 0.0,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="ruta al modelo (.pb o .onnx)")
    parser.add_argument("--input_size", nargs=2, type=int, required=False, help="resolución de entrada esperada (solo para wait_for_frame comparativa) ej: --input_size 640 360")
    parser.add_argument("--output_size", nargs=2, type=int, required=True, help="resolución de salida final (ancho alto)")
    parser.add_argument("--device", choices=["cpu","opencl","npu"], default="cpu")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iters", type=int, default=30)
    parser.add_argument("--save_example", action="store_true")
    args = parser.parse_args()

    model_path = args.model
    model_name = os.path.basename(model_path)
    out_w, out_h = args.output_size

    # Decide backend
    use_cv2 = False
    onnx_sess = None
    onnx_input = None
    onnx_c = onnx_h = onnx_w = None
    sr = None
    model_kind = None
    model_scale = None

    if model_path.endswith(".pb"):
        sr = dnn_superres.DnnSuperResImpl_create()
        # load model like before
        base = os.path.basename(model_path).upper()
        if "FSRCNN" in base:
            model_scale = int(base.split("_X")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("fsrcnn", model_scale)
            model_kind = "fsrcnn"
        elif "EDSR" in base:
            model_scale = int(base.split("_X")[-1].split(".")[0])
            sr.readModel(model_path)
            sr.setModel("edsr", model_scale)
            model_kind = "edsr"
        else:
            # fallback: try to read
            sr.readModel(model_path)
        sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
        if args.device == "cpu":
            sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        elif args.device == "opencl":
            sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
        else:
            print("[!] NPU no soportado por cv2.dnn_superres. Use ONNX/OpenVINO para NPU.")
        use_cv2 = True
    elif model_path.endswith(".onnx"):
        if not ONNX_AVAILABLE:
            print("[!] onnxruntime no instalado. Instala onnxruntime para usar modelos .onnx")
            return
        providers = ["CPUExecutionProvider"]
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        onnx_sess = ort.InferenceSession(model_path, providers=providers)
        onnx_input = onnx_sess.get_inputs()[0].name
        onnx_c, onnx_h, onnx_w = onnx_input_info(onnx_sess)
        print(f"[INFO] ONNX input inferred C,H,W = {onnx_c},{onnx_h},{onnx_w} (None = dinámico)")
    else:
        print("[!] Formato de modelo no soportado (solo .pb o .onnx)")
        return

    print(f"[*] Modelo: {model_name}, device={args.device}, output={out_w}x{out_h}, use_cv2={use_cv2}")

    # Warmup
    last_seq = 0
    print(f"[*] Esperando frames y haciendo {args.warmup} warm-up (si hay frames)...")
    warmed = 0
    for i in range(args.warmup):
        frame, w, h, seq = wait_for_frame(timeout=4.0, last_seq=last_seq)
        if frame is None:
            print("    [!] No frame en warmup (timeout)")
            time.sleep(0.1)
            continue
        last_seq = seq
        warmed += 1
        # prepare and run once (no measure)
        if use_cv2:
            prep = prepare_input_for_cv2_dnn(sr, frame, model_kind, model_scale, input_w=None, input_h=None)
            try:
                _ = sr.upsample(prep)
            except Exception as e:
                print(f"    [!] Error warmup cv2: {e}")
        else:
            want_c = onnx_c if onnx_c is not None else 3
            want_h = onnx_h
            want_w = onnx_w
            inp = prepare_input_for_onnx(frame, want_c, want_h, want_w)
            try:
                _ = onnx_sess.run(None, {onnx_input: inp})
            except Exception as e:
                print(f"    [!] Error warmup onnx: {e}")

    print(f"[*] Warmup frames procesados: {warmed}")

    # main loop for iters
    times_total = []
    times_pre = []
    times_inf = []
    times_post = []
    frames_ok = 0

    example_saved = False
    example_dir = "benchmark_examples"
    os.makedirs(example_dir, exist_ok=True)

    for i in range(args.iters):
        frame, w, h, seq = wait_for_frame(timeout=6.0, last_seq=last_seq)
        if frame is None:
            print(f"    [!] iter {i}: no frame disponible (timeout)")
            continue
        last_seq = seq

        # ----- PREPROC -----
        t0 = time.time()
        # Decide preprocessing according to model
        if use_cv2:
            # cv2 sr expects RGB HxW image and handles internal scale
            pre_img = frame  # frame already RGB
            # optionally resize to expected input if you know it; dnn_superres often takes variable input
        else:
            want_c = onnx_c if onnx_c is not None else 3
            want_h = onnx_h
            want_w = onnx_w
            pre_img_tensor = prepare_input_for_onnx(frame, want_c, want_h, want_w)
        t1 = time.time()

        # ----- INFERENCE -----
        try:
            if use_cv2:
                t_in_s = time.time()
                out = sr.upsample(pre_img)
                t_in_e = time.time()
                # out is HxWx3 (RGB)
            else:
                t_in_s = time.time()
                out_raw = onnx_sess.run(None, {onnx_input: pre_img_tensor})
                t_in_e = time.time()
                # postprocess out_raw to numpy HxWxC
                out0 = out_raw[0]
                # if NCHW
                if out0.ndim == 4:
                    out = out0[0].transpose(1,2,0)  # HWC
                elif out0.ndim == 3:
                    # CHW? or HWC? attempt heuristics
                    # if shape = (C,H,W)
                    if out0.shape[0] in (1,3) and out0.shape[1] > 1 and out0.shape[2] > 1:
                        out = out0.transpose(1,2,0)
                    else:
                        out = out0
                else:
                    out = out0
                # If output normalized 0..1, scale
                if out.dtype != np.uint8:
                    # try clip and scale if values between 0..1 or -1..1
                    mn, mx = out.min(), out.max()
                    if -1.1 < mn < 1.1 and -1.1 < mx < 1.1:
                        out = np.clip((out + 0.0) * 255.0, 0, 255).astype(np.uint8)
                    else:
                        # assume already 0..255
                        out = np.clip(out, 0, 255).astype(np.uint8)
        except Exception as e:
            print(f"    [!] Error durante inferencia: {e}")
            continue
        # ----- POSTPROC -----
        t_post_s = time.time()
        # Ensure out is HxWxC or HxW
        if out.ndim == 2:
            # single channel
            out_vis = out
        else:
            # if more than 3 channels, cut
            if out.shape[2] > 3:
                out_vis = out[:, :, :3]
            else:
                out_vis = out
        # If output isn't the target resolution, resize to out_w,out_h
        if out_vis.shape[1] != out_w or out_vis.shape[0] != out_h:
            out_resized = cv2.resize(out_vis, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
        else:
            out_resized = out_vis
        t_post_e = time.time()

        pre_ms = (t1 - t0) * 1000.0
        inf_ms = (t_in_e - t_in_s) * 1000.0
        post_ms = (t_post_e - t_post_s) * 1000.0
        total_ms = pre_ms + inf_ms + post_ms

        times_total.append(total_ms)
        times_pre.append(pre_ms)
        times_inf.append(inf_ms)
        times_post.append(post_ms)
        frames_ok += 1

        if args.save_example and not example_saved:
            fn = os.path.join(example_dir, f"{model_name}_{args.device}_{w}x{h}.png")
            # ensure correct color ordering for saving: if RGB -> BGR for cv2.imwrite
            if out_resized.ndim == 3 and out_resized.shape[2] == 3:
                cv2.imwrite(fn, cv2.cvtColor(out_resized, cv2.COLOR_RGB2BGR))
            else:
                cv2.imwrite(fn, out_resized)
            example_saved = True

        print(f"    [iter {i}] total={total_ms:.2f}ms (pre={pre_ms:.2f} inf={inf_ms:.2f} post={post_ms:.2f})")

    # End loop: results
    if frames_ok == 0:
        print("    -> No frames procesados")
        return

    arr_total = np.array(times_total)
    arr_pre = np.array(times_pre)
    arr_inf = np.array(times_inf)
    arr_post = np.array(times_post)

    s_total = stats_from_array(arr_total)
    s_pre = stats_from_array(arr_pre)
    s_inf = stats_from_array(arr_inf)
    s_post = stats_from_array(arr_post)

    print("RESULT SUMMARY:")
    print(f" frames: {frames_ok}")
    print(f" total mean/std/p50/p90/p99: {s_total['mean']:.2f}/{s_total['std']:.2f}/{s_total['p50']:.2f}/{s_total['p90']:.2f}/{s_total['p99']:.2f}")
    print(f" infer mean/p90: {s_inf['mean']:.2f}/{s_inf['p90']:.2f}")

    # Append to CSV
    csv_file = "benchmark_results_shm.csv"
    header = ["model","device","frames","total_mean_ms","total_std_ms","total_p50","total_p90","total_p99",
              "infer_mean_ms","infer_p90_ms","pre_mean_ms","post_mean_ms"]
    write_header = not os.path.isfile(csv_file)
    with open(csv_file, "a", newline="") as cf:
        writer = csv.writer(cf)
        if write_header:
            writer.writerow(header)
        writer.writerow([
            model_name,
            args.device,
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
