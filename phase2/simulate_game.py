#!/usr/bin/env python3
"""
simulate_game.py, Simulates a running game by writing frames into SHM.

Useful to test hybrid_pipeline.py without needing a real game.
Reads images from a folder (or a video file) and writes them to SHM
at a target FPS, exactly as wrapper_swapbuffers_shm.so would.

Usage:
    # From a folder of PNGs (e.g. tst_img/ at a specific resolution):
    python3 FASE_2/simulate_game.py --source tst_img/mine_960x540.png --fps 60 --loop

    # From a video file:
    python3 FASE_2/simulate_game.py --source /path/to/video.mp4 --fps 60

    # Single still image repeated:
    python3 FASE_2/simulate_game.py --source mine.png --res 960x540 --fps 60 --loop
"""

import argparse
import os
import posix_ipc
import mmap
import struct
import time

import cv2
import numpy as np

SHM_NAME  = "/framebuffer_shared"
HDR_FMT   = "IIII"
HDR_BYTES = 16


def write_frame_shm(shm_mem: mmap.mmap, bgr: np.ndarray, seq: int) -> None:
    h, w = bgr.shape[:2]
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    # Vertical flip: OpenGL origin is bottom-left, wrapper flips; we pre-flip here
    # so the pipeline reads it right-side-up (same as real game output).
    rgba_flipped = np.ascontiguousarray(rgba[::-1])
    shm_mem.seek(0)
    shm_mem.write(struct.pack(HDR_FMT, w, h, seq, 0))   # ready=0 while writing
    shm_mem.write(rgba_flipped.tobytes())
    shm_mem.seek(12)
    shm_mem.write(struct.pack("I", 1))                  # ready=1


def open_or_create_shm(w: int, h: int):
    total = HDR_BYTES + w * h * 4
    try:
        shm = posix_ipc.SharedMemory(SHM_NAME, posix_ipc.O_CREAT | posix_ipc.O_RDWR, size=total)
    except posix_ipc.ExistentialError:
        shm = posix_ipc.SharedMemory(SHM_NAME)
        if shm.size < total:
            shm.unlink()
            shm = posix_ipc.SharedMemory(SHM_NAME, posix_ipc.O_CREAT | posix_ipc.O_RDWR, size=total)
    mem = mmap.mmap(shm.fd, total)
    shm.close_fd()
    return shm, mem


def load_frames(source: str, res: str | None) -> list[np.ndarray]:
    frames = []
    if os.path.isfile(source):
        ext = os.path.splitext(source)[1].lower()
        if ext in (".mp4", ".avi", ".mkv", ".mov"):
            cap = cv2.VideoCapture(source)
            while True:
                ok, f = cap.read()
                if not ok:
                    break
                frames.append(f)
            cap.release()
        else:
            img = cv2.imread(source)
            if img is None:
                raise ValueError(f"Cannot read image: {source}")
            frames.append(img)
    elif os.path.isdir(source):
        files = sorted(f for f in os.listdir(source) if f.lower().endswith(".png"))
        for fn in files:
            img = cv2.imread(os.path.join(source, fn))
            if img is not None:
                frames.append(img)
    else:
        raise ValueError(f"Source not found: {source}")

    if not frames:
        raise ValueError(f"No frames loaded from {source}")

    if res:
        rw, rh = map(int, res.lower().split("x"))
        frames = [cv2.resize(f, (rw, rh), interpolation=cv2.INTER_AREA) for f in frames]

    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Image, image folder, or video file")
    ap.add_argument("--fps",    type=float, default=60.0)
    ap.add_argument("--res",    default=None, help="Force resolution WxH, e.g. 960x540")
    ap.add_argument("--loop",   action="store_true", help="Loop frames indefinitely")
    ap.add_argument("--max_frames", type=int, default=0, help="Stop after N frames (0=unlimited)")
    args = ap.parse_args()

    print(f"Loading frames from {args.source} ...")
    frames = load_frames(args.source, args.res)
    h, w   = frames[0].shape[:2]
    print(f"Loaded {len(frames)} frame(s) at {w}x{h}  →  SHM {SHM_NAME}")

    shm, mem = open_or_create_shm(w, h)
    frame_period = 1.0 / args.fps
    seq = 0
    total_written = 0

    print(f"Writing to SHM at {args.fps} FPS (Ctrl+C to stop) ...")
    try:
        idx = 0
        while True:
            t0 = time.perf_counter()
            write_frame_shm(mem, frames[idx], seq)
            seq += 1
            total_written += 1
            idx = (idx + 1) % len(frames)
            if not args.loop and idx == 0:
                break
            if args.max_frames and total_written >= args.max_frames:
                break
            elapsed = time.perf_counter() - t0
            sleep_t = frame_period - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        mem.close()
        shm.unlink()
        print(f"SHM unlinked. Total frames written: {total_written}")


if __name__ == "__main__":
    main()
