"""Fase 2, Matriz de calidad: arquitectura híbrida vs bicúbico.

Compara, con downsampling controlado y pixel-aligned, la reconstrucción del
pipeline híbrido (render bajo + FSRCNN/OpenVINO en iGPU) frente al baseline
bicúbico, tomando como verdad de referencia (ground truth) un frame nativo a
resolución completa.

Metodología (por cada escala):
  1. GT nativo (p. ej. 1920x1080)  →  downsample a la resolución de entrada
     (simula el render de bajo coste de la dGPU).
  2. Híbrido  = FSRCNN sobre Y (OpenVINO) + croma bicúbico  →  vuelta a 1080p.
  3. Bicúbico = upscale bicúbico directo  →  vuelta a 1080p.
  4. Métricas PSNR/SSIM de (híbrido vs GT) y (bicúbico vs GT).

El método de superresolución es idéntico al de phase2/hybrid_pipeline.py.

Uso:
  python3 phase2/quality_matrix.py \
      --gt results/sample_frames/mine_1920x1080.png \
      --out_dir results/phase2_quality --device GPU
"""
import argparse
import os

import cv2
import numpy as np
import openvino as ov
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# escala -> resolución de entrada que produce salida ~1080p
SCALE_INPUT = {4: (480, 270), 3: (640, 360), 2: (960, 540)}


def sr_fsrcnn(req, bgr, out_wh):
    """FSRCNN sobre Y + croma bicúbico (idéntico a hybrid_pipeline.sr_frame)."""
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32) / 255.0
    req.infer({0: y[None, :, :, None]})
    out_y = (np.squeeze(req.get_output_tensor(0).data) * 255.0).clip(0, 255).astype(np.uint8)
    oh, ow = out_y.shape
    cr = cv2.resize(ycrcb[:, :, 1], (ow, oh), interpolation=cv2.INTER_CUBIC)
    cb = cv2.resize(ycrcb[:, :, 2], (ow, oh), interpolation=cv2.INTER_CUBIC)
    sr = cv2.cvtColor(cv2.merge([out_y, cr, cb]), cv2.COLOR_YCrCb2BGR)
    if (ow, oh) != out_wh:
        sr = cv2.resize(sr, out_wh, interpolation=cv2.INTER_CUBIC)
    return sr


def metrics(a, b):
    return float(psnr(a, b, data_range=255)), float(ssim(a, b, channel_axis=2, data_range=255))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", default="results/sample_frames/mine_1920x1080.png")
    ap.add_argument("--out_dir", default="results/phase2_quality")
    ap.add_argument("--device", default="GPU")
    args = ap.parse_args()

    gt = cv2.imread(args.gt)
    if gt is None:
        raise SystemExit(f"No se pudo leer GT: {args.gt}")
    gh, gw = gt.shape[:2]
    out_wh = (gw, gh)
    os.makedirs(args.out_dir, exist_ok=True)

    core = ov.Core()
    dev = args.device if args.device in core.available_devices else "CPU"
    print(f"[INFO] GT {gw}x{gh} | dispositivo {dev}")

    rows = []
    for scale, (iw, ih) in SCALE_INPUT.items():
        model_xml = os.path.join(REPO_DIR, "models", "openvino_ir", f"FSRCNN_x{scale}.xml")
        m = core.read_model(model_xml)
        m.reshape([1, ih, iw, 1])
        req = core.compile_model(m, dev, {"CACHE_DIR": "/tmp/openvino_cache"}).create_infer_request()

        low = cv2.resize(gt, (iw, ih), interpolation=cv2.INTER_CUBIC)  # LR bicubico: coincide con el entrenamiento de FSRCNN
        hybrid = sr_fsrcnn(req, low, out_wh)
        bicubic = cv2.resize(low, out_wh, interpolation=cv2.INTER_CUBIC)

        p_h, s_h = metrics(gt, hybrid)
        p_b, s_b = metrics(gt, bicubic)
        rows.append((scale, f"{iw}x{ih}", p_b, s_b, p_h, s_h, p_h - p_b, s_h - s_b))
        print(f"  x{scale} ({iw}x{ih}): bicubico {p_b:.2f} dB / {s_b:.3f}  |  "
              f"hibrido {p_h:.2f} dB / {s_h:.3f}  |  +{p_h-p_b:.2f} dB")

        # imagen comparativa (recorte central para apreciar detalle)
        cy, cx = gh // 2, gw // 2
        crop = lambda im: im[cy-135:cy+135, cx-240:cx+240]
        triptico = np.hstack([crop(gt), crop(bicubic), crop(hybrid)])
        cv2.imwrite(os.path.join(args.out_dir, f"compare_x{scale}_{iw}x{ih}.png"), triptico)

    csv = os.path.join(args.out_dir, "quality_matrix.csv")
    with open(csv, "w") as f:
        f.write("scale,input_res,psnr_bicubic,ssim_bicubic,psnr_hybrid,ssim_hybrid,psnr_gain,ssim_gain\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]:.3f},{r[3]:.4f},{r[4]:.3f},{r[5]:.4f},{r[6]:.3f},{r[7]:.4f}\n")
    print(f"[INFO] CSV: {csv}")
    print("[INFO] Recortes comparativos GT|bicubico|hibrido en", args.out_dir)


if __name__ == "__main__":
    main()
