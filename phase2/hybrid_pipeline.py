#!/usr/bin/env python3
"""
hybrid_pipeline.py, Real-time hybrid iGPU+dGPU super-resolution pipeline.

Architecture:
    dGPU renders game at low resolution
    → wrapper_swapbuffers_shm.so writes frame to SHM (/dev/shm/framebuffer_shared)
    → this script reads SHM on iGPU, applies FSRCNN IR via OpenVINO GPU
    → saves upscaled frames + optional display window

Usage:
    python3 FASE_2/hybrid_pipeline.py \\
        --model models/openvino_ir/FSRCNN_x2.xml --scale 2 \\
        --max_frames 300 --out_dir phase2/results \\
        [--display] [--save_lowres] [--device GPU]
"""

import argparse
import mmap
import os
import struct
import time

import cv2
import numpy as np
import openvino as ov

SHM_PATH  = "/dev/shm/framebuffer_shared"
HDR_FMT   = "IIII"   # width, height, seq, ready  (4 × uint32_t)
HDR_BYTES = 16


# ── SHM helpers ──────────────────────────────────────────────────────────────

def wait_shm_ready(timeout: float = 60.0) -> tuple[int, int]:
    """Block until SHM exists and contains a valid first frame. Returns (w, h)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not os.path.exists(SHM_PATH):
            time.sleep(0.2)
            continue
        try:
            with open(SHM_PATH, "rb") as f:
                raw = f.read(HDR_BYTES)
            if len(raw) < HDR_BYTES:
                time.sleep(0.1)
                continue
            w, h, _, ready = struct.unpack(HDR_FMT, raw)
            if w > 0 and h > 0 and ready == 1:
                return w, h
        except OSError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"SHM not ready after {timeout}s. Is the game running with LD_PRELOAD?")


def read_frame(mm: mmap.mmap, w: int, h: int, last_seq: int) -> tuple[np.ndarray | None, int]:
    """Non-blocking read. Returns (bgr_frame, new_seq) or (None, last_seq)."""
    mm.seek(0)
    raw = mm.read(HDR_BYTES)
    fw, fh, seq, ready = struct.unpack(HDR_FMT, raw)
    if ready != 1 or seq == last_seq or fw != w or fh != h:
        return None, last_seq
    frame_bytes = mm.read(w * h * 4)
    if len(frame_bytes) < w * h * 4:
        return None, last_seq
    rgba = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(h, w, 4).copy()
    bgr  = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    return bgr, seq


# ── OpenVINO model ────────────────────────────────────────────────────────────

def load_model(model_path: str, input_w: int, input_h: int, device: str = "GPU"):
    core  = ov.Core()
    model = core.read_model(model_path)
    inp   = model.input(0)
    # FSRCNN converted from TF .pb uses NHWC layout
    model.reshape({inp.any_name: [1, input_h, input_w, 1]})
    compiled = core.compile_model(model, device)
    req      = compiled.create_infer_request()
    return req, inp.any_name, compiled.output(0)


def sr_frame(req, input_name, scale: int, bgr: np.ndarray) -> np.ndarray:
    """Apply FSRCNN super-resolution on Y channel, bicubic-upscale Cb/Cr."""
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y     = ycrcb[:, :, 0].astype(np.float32) / 255.0
    req.infer({input_name: y[None, :, :, None]})
    out   = req.get_output_tensor(0).data
    # La salida del IR FSRCNN es NCHW (1,1,H,W); squeeze deja (H,W) sin
    # depender del layout (NCHW o NHWC, ambos con un único canal Y).
    out_y = (np.squeeze(out) * 255.0).clip(0, 255).astype(np.uint8)
    oh, ow = out_y.shape
    cr_up = cv2.resize(ycrcb[:, :, 1], (ow, oh), interpolation=cv2.INTER_CUBIC)
    cb_up = cv2.resize(ycrcb[:, :, 2], (ow, oh), interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(np.stack([out_y, cr_up, cb_up], axis=2), cv2.COLOR_YCrCb2BGR)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",      default="models/openvino_ir/FSRCNN_x2.xml")
    ap.add_argument("--scale",      type=int, default=2)
    ap.add_argument("--device",     default="GPU", help="OpenVINO device (GPU = Intel iGPU)")
    ap.add_argument("--max_frames", type=int, default=300)
    ap.add_argument("--out_dir",    default="phase2/results")
    ap.add_argument("--display",    action="store_true", help="Show live upscaled window")
    ap.add_argument("--save_lowres",action="store_true", help="Also save low-res + bicubic frames")
    ap.add_argument("--shm_timeout",type=float, default=60.0)
    args = ap.parse_args()

    for sub in ("hybrid_frames", "lowres_frames", "bicubic_frames"):
        os.makedirs(os.path.join(args.out_dir, sub), exist_ok=True)

    print(f"Waiting for game SHM at {SHM_PATH} (timeout {args.shm_timeout}s) ...")
    w, h = wait_shm_ready(args.shm_timeout)
    ow, oh = w * args.scale, h * args.scale
    print(f"Game resolution: {w}x{h}  →  SR output: {ow}x{oh}")

    print(f"Loading {args.model} on {args.device} ...")
    req, input_name, _ = load_model(args.model, w, h, args.device)
    print("Model ready.")

    shm_size = HDR_BYTES + w * h * 4
    fd = os.open(SHM_PATH, os.O_RDONLY)
    mm = mmap.mmap(fd, shm_size, access=mmap.ACCESS_READ)

    frame_idx = 0
    last_seq  = 0
    latencies = []

    print(f"Capturing {args.max_frames} frames (press Q in display window to stop early) ...")
    try:
        while frame_idx < args.max_frames:
            bgr, last_seq = read_frame(mm, w, h, last_seq)
            if bgr is None:
                time.sleep(0.001)
                continue

            t0       = time.perf_counter()
            upscaled = sr_frame(req, input_name, args.scale, bgr)
            lat_ms   = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat_ms)

            fname = f"{frame_idx:05d}.png"
            cv2.imwrite(os.path.join(args.out_dir, "hybrid_frames", fname), upscaled)

            if args.save_lowres:
                cv2.imwrite(os.path.join(args.out_dir, "lowres_frames",  fname), bgr)
                bicubic = cv2.resize(bgr, (ow, oh), interpolation=cv2.INTER_CUBIC)
                cv2.imwrite(os.path.join(args.out_dir, "bicubic_frames", fname), bicubic)

            if args.display:
                disp = upscaled.copy()
                fps_str = f"FSRCNN x{args.scale} iGPU  {1000/lat_ms:.1f} FPS  ({lat_ms:.1f} ms)"
                cv2.putText(disp, fps_str, (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                            0.75, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow("Hybrid SR Output", disp)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Stopped by user.")
                    break

            frame_idx += 1
            if frame_idx % 50 == 0:
                recent = latencies[-50:]
                print(f"  [{frame_idx:4d}/{args.max_frames}]  "
                      f"avg {np.mean(recent):.1f} ms  "
                      f"({1000/np.mean(recent):.1f} FPS)")

    finally:
        mm.close()
        os.close(fd)
        if args.display:
            cv2.destroyAllWindows()

    if latencies:
        avg_ms = float(np.mean(latencies))
        p95_ms = float(np.percentile(latencies, 95))
        print(f"\n=== Pipeline summary ===")
        print(f"  Frames captured : {frame_idx}")
        print(f"  SR avg latency  : {avg_ms:.2f} ms  →  {1000/avg_ms:.1f} FPS")
        print(f"  SR p95 latency  : {p95_ms:.2f} ms")
        print(f"  Hybrid frames   : {args.out_dir}/hybrid_frames/")

        stats_path = os.path.join(args.out_dir, "pipeline_stats.txt")
        with open(stats_path, "w") as f:
            f.write(f"model={args.model}\n")
            f.write(f"device={args.device}\n")
            f.write(f"scale={args.scale}\n")
            f.write(f"input_res={w}x{h}\n")
            f.write(f"output_res={ow}x{oh}\n")
            f.write(f"frames={frame_idx}\n")
            f.write(f"avg_latency_ms={avg_ms:.3f}\n")
            f.write(f"avg_fps={1000/avg_ms:.2f}\n")
            f.write(f"p95_latency_ms={p95_ms:.3f}\n")
        print(f"  Stats           : {stats_path}")


if __name__ == "__main__":
    main()
