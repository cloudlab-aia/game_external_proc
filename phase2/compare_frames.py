#!/usr/bin/env python3
"""
compare_frames.py — Frame-by-frame PSNR/SSIM comparison between SR methods.

Compares hybrid FSRCNN frames vs bicubic baseline, and optionally vs a
native reference render (same scene captured at full resolution).

Usage:
    # Hybrid vs bicubic only (no native reference):
    python3 FASE_2/compare_frames.py \\
        --hybrid  phase2/results/hybrid_frames \\
        --bicubic phase2/results/bicubic_frames \\
        --out_csv phase2/results/comparison_metrics.csv

    # Hybrid vs bicubic vs native reference:
    python3 FASE_2/compare_frames.py \\
        --hybrid  phase2/results/hybrid_frames \\
        --bicubic phase2/results/bicubic_frames \\
        --native  phase2/results/native_frames \\
        --out_csv phase2/results/comparison_metrics.csv \\
        --save_diff_images phase2/results/comparison_images
"""

import argparse
import csv
import os

import cv2
import numpy as np
from skimage.metrics import peak_signal_noise_ratio as calc_psnr
from skimage.metrics import structural_similarity as calc_ssim


def load_dir(path: str) -> list[tuple[str, np.ndarray]]:
    files = sorted(f for f in os.listdir(path) if f.lower().endswith(".png"))
    result = []
    for fn in files:
        img = cv2.imread(os.path.join(path, fn))
        if img is not None:
            result.append((fn, img))
    return result


def match_size(ref: np.ndarray, img: np.ndarray) -> np.ndarray:
    if img.shape[:2] != ref.shape[:2]:
        return cv2.resize(img, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_CUBIC)
    return img


def metrics(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    p = calc_psnr(a, b, data_range=255)
    s = calc_ssim(a, b, channel_axis=2, data_range=255)
    return float(p), float(s)


def save_comparison(path: str, ref: np.ndarray, bicubic: np.ndarray, hybrid: np.ndarray,
                    fname: str, p_bic: float, p_hyb: float) -> None:
    h = max(ref.shape[0], bicubic.shape[0], hybrid.shape[0])
    def pad(img):
        if img.shape[0] < h:
            img = cv2.resize(img, (img.shape[1], h))
        return img
    ref_p, bic_p, hyb_p = pad(ref), pad(bicubic), pad(hybrid)

    def label(img, text):
        out = img.copy()
        cv2.putText(out, text, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,0), 2, cv2.LINE_AA)
        return out

    row = np.hstack([
        label(ref_p,  "Native (reference)"),
        label(bic_p,  f"Bicubic  PSNR={p_bic:.1f}dB"),
        label(hyb_p,  f"FSRCNN SR  PSNR={p_hyb:.1f}dB"),
    ])
    cv2.imwrite(os.path.join(path, fname), row)


def print_summary(label: str, vals: list[float], unit: str = "") -> None:
    if not vals:
        return
    a  = np.mean(vals)
    lo = np.min(vals)
    hi = np.max(vals)
    print(f"  {label:40s}  avg={a:.4f}{unit}  min={lo:.4f}  max={hi:.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hybrid",  required=True)
    ap.add_argument("--bicubic", required=True)
    ap.add_argument("--native",  default=None)
    ap.add_argument("--out_csv", default="phase2/results/comparison_metrics.csv")
    ap.add_argument("--save_diff_images", default=None)
    args = ap.parse_args()

    print("Loading frames ...")
    hyb_frames = load_dir(args.hybrid)
    bic_frames = load_dir(args.bicubic)
    nat_frames = load_dir(args.native) if args.native and os.path.isdir(args.native) else []

    n = min(len(hyb_frames), len(bic_frames))
    if nat_frames:
        n = min(n, len(nat_frames))
    print(f"Comparing {n} frames (hybrid={len(hyb_frames)} bicubic={len(bic_frames)}"
          + (f" native={len(nat_frames)}" if nat_frames else "") + ")")

    if args.save_diff_images:
        os.makedirs(args.save_diff_images, exist_ok=True)

    rows = []
    p_hyb_bic, s_hyb_bic   = [], []
    p_hyb_nat, s_hyb_nat   = [], []
    p_bic_nat, s_bic_nat   = [], []

    for i in range(n):
        fname, hyb = hyb_frames[i]
        _,     bic = bic_frames[i]
        bic = match_size(hyb, bic)

        row: dict = {"frame": fname}

        if nat_frames:
            _, nat = nat_frames[i]
            nat = match_size(hyb, nat)
            ph, sh = metrics(nat, hyb)
            pb, sb = metrics(nat, bic)
            row["psnr_hybrid_vs_native"]  = f"{ph:.4f}"
            row["ssim_hybrid_vs_native"]  = f"{sh:.4f}"
            row["psnr_bicubic_vs_native"] = f"{pb:.4f}"
            row["ssim_bicubic_vs_native"] = f"{sb:.4f}"
            p_hyb_nat.append(ph); s_hyb_nat.append(sh)
            p_bic_nat.append(pb); s_bic_nat.append(sb)
            if args.save_diff_images:
                save_comparison(args.save_diff_images, nat, bic, hyb, fname, pb, ph)
        else:
            ph, sh = metrics(bic, hyb)
            row["psnr_hybrid_vs_bicubic"] = f"{ph:.4f}"
            row["ssim_hybrid_vs_bicubic"] = f"{sh:.4f}"
            p_hyb_bic.append(ph); s_hyb_bic.append(sh)

        rows.append(row)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{n} ...")

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    with open(args.out_csv, "w", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

    print(f"\n=== Results ({n} frames) ===")
    if nat_frames:
        print_summary("PSNR  FSRCNN vs native",  p_hyb_nat, " dB")
        print_summary("SSIM  FSRCNN vs native",  s_hyb_nat)
        print_summary("PSNR  Bicubic vs native", p_bic_nat, " dB")
        print_summary("SSIM  Bicubic vs native", s_bic_nat)
        if p_hyb_nat and p_bic_nat:
            delta = np.mean(p_hyb_nat) - np.mean(p_bic_nat)
            print(f"\n  FSRCNN advantage over bicubic: {delta:+.2f} dB PSNR")
    else:
        print_summary("PSNR  FSRCNN vs bicubic", p_hyb_bic, " dB")
        print_summary("SSIM  FSRCNN vs bicubic", s_hyb_bic)

    print(f"\n  CSV written: {args.out_csv}")
    if args.save_diff_images:
        print(f"  Comparison images: {args.save_diff_images}")


if __name__ == "__main__":
    main()
