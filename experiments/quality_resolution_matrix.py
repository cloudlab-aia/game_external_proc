"""Matriz completa calidad/latencia: TODA resolución de entrada × cada escala.

Para cada (resolución de entrada, factor de escala) con FSRCNN:
  1. Frame nativo de referencia (GT 1920x1080, captura real de Minecraft).
  2. GT_salida = GT remuestreado a la resolución de salida (entrada × escala).
  3. low = GT remuestreado a la resolución de entrada (render de bajo coste).
  4. híbrido = FSRCNN(low)   |   bicúbico = upscale(low)
  5. PSNR/SSIM de (híbrido vs GT_salida) y (bicúbico vs GT_salida).
  6. latencia de inferencia (iGPU) por frame.

Genera CSV + gráficas (calidad vs resolución por escala; latencia vs resolución)
+ recortes comparativos. Todo offline y reproducible.

Uso:
  python3 experiments/quality_resolution_matrix.py \
      --gt results/sample_frames/mine_1920x1080.png \
      --out_dir results/experiments/quality_matrix
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

# Resoluciones de entrada (16:9, típicas de render bajo) y escalas
INPUT_RES = [(256, 144), (320, 180), (426, 240), (480, 270),
             (640, 360), (854, 480), (960, 540)]
SCALES = [2, 3, 4]


def sr_fsrcnn(req, bgr):
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
    ap.add_argument("--gt", default="results/sample_frames/mine_1920x1080.png")
    ap.add_argument("--out_dir", default="results/experiments/quality_matrix")
    ap.add_argument("--device", default="GPU")
    ap.add_argument("--iters", type=int, default=20)
    args = ap.parse_args()

    gt_master = cv2.imread(args.gt)
    if gt_master is None:
        raise SystemExit(f"No se pudo leer GT: {args.gt}")
    GW, GH = gt_master.shape[1], gt_master.shape[0]
    os.makedirs(args.out_dir, exist_ok=True)
    crops_dir = os.path.join(args.out_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)

    core = ov.Core()
    dev = args.device if args.device in core.available_devices else "CPU"
    print(f"[INFO] GT {GW}x{GH} | dispositivo {dev}")

    # compilar un IR reshape por (escala, resolución)
    rows = []
    for scale in SCALES:
        ir = os.path.join(REPO, "models", "openvino_ir", f"FSRCNN_x{scale}.xml")
        for (iw, ih) in INPUT_RES:
            ow, oh = iw * scale, ih * scale
            if ow > GW or oh > GH:
                continue  # salida mayor que el GT: no hay referencia
            # referencia y entrada por remuestreo controlado
            gt_out = cv2.resize(gt_master, (ow, oh), interpolation=cv2.INTER_AREA)
            low = cv2.resize(gt_master, (iw, ih), interpolation=cv2.INTER_CUBIC)

            m = core.read_model(ir)
            m.reshape([1, ih, iw, 1])
            req = core.compile_model(m, dev, {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()

            # latencia inferencia (warmup + iters)
            for _ in range(3):
                sr_fsrcnn(req, low)
            t = time.perf_counter()
            for _ in range(args.iters):
                hybrid = sr_fsrcnn(req, low)
            infer_ms = (time.perf_counter() - t) / args.iters * 1000

            bicubic = cv2.resize(low, (ow, oh), interpolation=cv2.INTER_CUBIC)
            ph = float(psnr(gt_out, hybrid, data_range=255))
            sh = float(ssim(gt_out, hybrid, channel_axis=2, data_range=255))
            pb = float(psnr(gt_out, bicubic, data_range=255))
            sb = float(ssim(gt_out, bicubic, channel_axis=2, data_range=255))
            fps = 1000 / infer_ms if infer_ms else 0

            rows.append(dict(scale=scale, in_w=iw, in_h=ih, out_w=ow, out_h=oh,
                             infer_ms=round(infer_ms, 2), infer_fps=round(fps, 1),
                             psnr_bicubic=round(pb, 3), ssim_bicubic=round(sb, 4),
                             psnr_hybrid=round(ph, 3), ssim_hybrid=round(sh, 4),
                             psnr_gain=round(ph - pb, 3), ssim_gain=round(sh - sb, 4)))
            print(f"  x{scale} {iw}x{ih}->{ow}x{oh}: "
                  f"hib {ph:.2f}dB/{sh:.3f} bic {pb:.2f}dB/{sb:.3f} "
                  f"(+{ph-pb:+.2f}dB) | IA {infer_ms:.1f}ms ({fps:.0f}FPS)")

            # recorte comparativo central GT|bicubico|hibrido
            cy, cx = oh // 2, ow // 2
            hh = min(135, oh // 2 - 1); hw = min(240, ow // 2 - 1)
            crop = lambda im: im[cy - hh:cy + hh, cx - hw:cx + hw]
            tri = np.hstack([crop(gt_out), crop(bicubic), crop(hybrid)])
            cv2.imwrite(os.path.join(crops_dir, f"x{scale}_{iw}x{ih}.png"), tri)

    # CSV
    csv_path = os.path.join(args.out_dir, "quality_resolution_matrix.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n[INFO] CSV: {csv_path}  ({len(rows)} combinaciones)")

    # gráficas
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plot_dir = os.path.join(args.out_dir, "plots")
        os.makedirs(plot_dir, exist_ok=True)
        cols = {2: "#27ae60", 3: "#2980b9", 4: "#c0392b"}

        # PSNR híbrido vs resolución de entrada, por escala
        plt.figure(figsize=(8, 5))
        for s in SCALES:
            pts = sorted([(r["in_w"] * r["in_h"], r["psnr_hybrid"]) for r in rows if r["scale"] == s])
            if pts:
                plt.plot([p[0] / 1000 for p in pts], [p[1] for p in pts], "o-",
                         color=cols[s], label=f"FSRCNN x{s}")
        plt.xlabel("Píxeles de entrada (miles)"); plt.ylabel("PSNR híbrido vs GT (dB)")
        plt.title("Calidad vs resolución de render, por factor de escala")
        plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, "psnr_vs_resolucion.png"), dpi=130); plt.close()

        # Latencia vs resolución de entrada, por escala
        plt.figure(figsize=(8, 5))
        for s in SCALES:
            pts = sorted([(r["in_w"] * r["in_h"], r["infer_ms"]) for r in rows if r["scale"] == s])
            if pts:
                plt.plot([p[0] / 1000 for p in pts], [p[1] for p in pts], "o-",
                         color=cols[s], label=f"FSRCNN x{s}")
        plt.axhline(16.6, color="gray", ls="--", alpha=0.6, label="60 FPS (16.6 ms)")
        plt.xlabel("Píxeles de entrada (miles)"); plt.ylabel("Latencia inferencia iGPU (ms)")
        plt.title("Coste de inferencia vs resolución de entrada")
        plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
        plt.savefig(os.path.join(plot_dir, "latencia_vs_resolucion.png"), dpi=130); plt.close()
        print(f"[INFO] gráficas en {plot_dir}")
    except Exception as e:
        print(f"[WARN] gráficas: {e}")


if __name__ == "__main__":
    main()
