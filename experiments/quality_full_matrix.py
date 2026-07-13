"""Matriz calidad ENTRADA × SALIDA completa (720p→4K) con todos los factores.

Rejilla: cada resolución de entrada 16:9 típica (render bajo) × cada resolución
de salida estándar (display). El factor de escala efectivo = salida/entrada
(cubre todos los factores que surgen). El método híbrido replica el pipeline
real: FSRCNN al factor entero más cercano (×2/×3/×4) + resize bicúbico al tamaño
de salida exacto (idéntico a processing/display_overlay y phase2).

Referencia (ground truth): UN frame nativo real a 4K (3840×2160). Para cada
salida, el GT se obtiene remuestreando el master a esa resolución (downsample, no
inventa detalle). Para cada entrada, el "render bajo" se obtiene remuestreando el
master a esa resolución.

Uso:
  python3 experiments/quality_full_matrix.py \
      --master results/sample_frames/mine_3840x2160.png \
      --out_dir results/experiments/quality_full --device GPU
"""
import argparse
import csv
import os
import time

import cv2
import numpy as np
import openvino as ov
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Entradas 16:9 típicas (resoluciones de render)
INPUTS = [(256, 144), (320, 180), (426, 240), (480, 270), (640, 360),
          (768, 432), (854, 480), (960, 540), (1152, 648), (1280, 720),
          (1600, 900), (1920, 1080)]
# Salidas estándar de display 16:9
OUTPUTS = [(1280, 720), (1920, 1080), (2560, 1440), (3840, 2160)]
OUT_NAME = {(1280, 720): "720p", (1920, 1080): "1080p",
            (2560, 1440): "1440p", (3840, 2160): "4K"}


def sr_fsrcnn(req, bgr):
    """FSRCNN sobre Y + croma bicúbico → salida = entrada × factor del modelo."""
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32) / 255.0
    req.infer({0: y[None, :, :, None]})
    out_y = (np.squeeze(req.get_output_tensor(0).data) * 255.0).clip(0, 255).astype(np.uint8)
    oh, ow = out_y.shape
    cr = cv2.resize(ycrcb[:, :, 1], (ow, oh), interpolation=cv2.INTER_CUBIC)
    cb = cv2.resize(ycrcb[:, :, 2], (ow, oh), interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(cv2.merge([out_y, cr, cb]), cv2.COLOR_YCrCb2BGR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default="results/sample_frames/mine_3840x2160.png")
    ap.add_argument("--out_dir", default="results/experiments/quality_full")
    ap.add_argument("--device", default="GPU")
    ap.add_argument("--iters", type=int, default=15)
    args = ap.parse_args()

    master = cv2.imread(args.master)
    if master is None:
        raise SystemExit(f"No se pudo leer el master 4K: {args.master}\n"
                         "Captura primero un frame nativo real a 3840x2160.")
    MW, MH = master.shape[1], master.shape[0]
    if MW < 3840 or MH < 2160:
        print(f"[AVISO] master {MW}x{MH} < 4K: las salidas mayores que el master se omiten.")
    os.makedirs(args.out_dir, exist_ok=True)

    core = ov.Core()
    dev = args.device if args.device in core.available_devices else "CPU"
    print(f"[INFO] master {MW}x{MH} | dispositivo {dev}")

    # cache de infer-requests por (factor, entrada)
    req_cache = {}

    def get_req(factor, iw, ih):
        key = (factor, iw, ih)
        if key not in req_cache:
            ir = os.path.join(REPO, "models", "openvino_ir", f"FSRCNN_x{factor}.xml")
            m = core.read_model(ir)
            m.reshape([1, ih, iw, 1])
            req_cache[key] = core.compile_model(
                m, dev, {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()
        return req_cache[key]

    rows = []
    for (ow, oh) in OUTPUTS:
        if ow > MW or oh > MH:
            print(f"[skip] salida {OUT_NAME[(ow,oh)]} > master")
            continue
        gt = cv2.resize(master, (ow, oh), interpolation=cv2.INTER_AREA)  # referencia a esa salida
        for (iw, ih) in INPUTS:
            if iw >= ow:  # la entrada debe ser menor que la salida
                continue
            scale_eff = oh / ih
            factor = min(4, max(2, round(ow / iw)))  # modelo FSRCNN más cercano
            # Render bajo por downsampling bicúbico del GT (protocolo SR estándar:
            # FSRCNN se entrena/evalúa con degradación bicúbica, Set5/Set14).
            low = cv2.resize(gt, (iw, ih), interpolation=cv2.INTER_CUBIC)

            req = get_req(factor, iw, ih)
            for _ in range(3):
                sr = sr_fsrcnn(req, low)
            t = time.perf_counter()
            for _ in range(args.iters):
                sr = sr_fsrcnn(req, low)
            infer_ms = (time.perf_counter() - t) / args.iters * 1000

            # ajustar al tamaño de salida exacto (igual que el pipeline real)
            hybrid = sr if (sr.shape[1], sr.shape[0]) == (ow, oh) else \
                cv2.resize(sr, (ow, oh), interpolation=cv2.INTER_CUBIC)
            bicubic = cv2.resize(low, (ow, oh), interpolation=cv2.INTER_CUBIC)

            ph = float(psnr(gt, hybrid, data_range=255)); sh = float(ssim(gt, hybrid, channel_axis=2, data_range=255))
            pb = float(psnr(gt, bicubic, data_range=255)); sb = float(ssim(gt, bicubic, channel_axis=2, data_range=255))
            rows.append(dict(salida=OUT_NAME[(ow, oh)], out_w=ow, out_h=oh,
                             in_w=iw, in_h=ih, scale_eff=round(scale_eff, 2),
                             fsrcnn=f"x{factor}", infer_ms=round(infer_ms, 2),
                             infer_fps=round(1000 / infer_ms, 1),
                             psnr_bicubic=round(pb, 3), ssim_bicubic=round(sb, 4),
                             psnr_hybrid=round(ph, 3), ssim_hybrid=round(sh, 4),
                             psnr_gain=round(ph - pb, 3), ssim_gain=round(sh - sb, 4)))
            print(f"  {OUT_NAME[(ow,oh)]:5s} <- {iw}x{ih} (x{scale_eff:.2f}, FSRCNN x{factor}): "
                  f"hib {ph:.2f}dB bic {pb:.2f}dB ({ph-pb:+.2f}) | IA {infer_ms:.1f}ms")

    if not rows:
        raise SystemExit("Sin combinaciones (¿master demasiado pequeño?).")
    csv_path = os.path.join(args.out_dir, "quality_full_matrix.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\n[INFO] CSV: {csv_path}  ({len(rows)} combinaciones)")

    # gráficas: PSNR vs entrada por salida; latencia vs entrada por salida
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        pd = os.path.join(args.out_dir, "plots"); os.makedirs(pd, exist_ok=True)
        cols = {"720p": "#27ae60", "1080p": "#2980b9", "1440p": "#8e44ad", "4K": "#c0392b"}
        for metric, ylab, fn in [("psnr_hybrid", "PSNR híbrido vs GT (dB)", "psnr_vs_entrada.png"),
                                 ("infer_ms", "Latencia inferencia iGPU (ms)", "latencia_vs_entrada.png")]:
            plt.figure(figsize=(9, 5))
            for out in ["720p", "1080p", "1440p", "4K"]:
                pts = sorted([(r["in_w"] * r["in_h"], r[metric]) for r in rows if r["salida"] == out])
                if pts:
                    plt.plot([p[0] / 1000 for p in pts], [p[1] for p in pts], "o-",
                             color=cols[out], label=f"salida {out}")
            if metric == "infer_ms":
                plt.axhline(16.6, color="gray", ls="--", alpha=0.6, label="60 FPS (16.6 ms)")
            plt.xlabel("Píxeles de entrada (miles)"); plt.ylabel(ylab)
            plt.title(ylab + " vs resolución de render, por salida")
            plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
            plt.savefig(os.path.join(pd, fn), dpi=130); plt.close()
        print(f"[INFO] gráficas en {pd}")
    except Exception as e:
        print(f"[WARN] gráficas: {e}")


if __name__ == "__main__":
    main()
