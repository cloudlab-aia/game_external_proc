#!/usr/bin/env python3
"""Latencia por componente del pipeline hibrido.

Mide, por frame, el coste de cada etapa del consumidor:
  lectura shm -> preproceso -> inferencia (iGPU) -> postproceso -> presentacion

La captura (wrapper, glReadPixels + copia a shm) se mide aparte en el
propio wrapper (ver Exp. 2); aqui se cubre el resto de la cadena.

Uso:  CUDA_VISIBLE_DEVICES="" python3 latency_components.py \
          --scale 3 --out_w 1920 --out_h 1080 --frames 300 [--no_display]
"""
import argparse
import struct
import time

import cv2
import numpy as np

SHM = "/dev/shm/framebuffer_shared"
HDR = struct.calcsize("IIII")
MODELS = "/home/ogg/Desktop/AIA/game_external_proc/models/openvino_ir"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--out_w", type=int, default=1920)
    ap.add_argument("--out_h", type=int, default=1080)
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--warmup", type=int, default=30)
    ap.add_argument("--no_display", action="store_true")
    ap.add_argument("--stale_ok", action="store_true",
                    help="Tras el primer frame, no esperar frames nuevos: "
                         "repite el ultimo (el coste por etapa no depende "
                         "del contenido). Util si el juego pausa sin foco.")
    ap.add_argument("--win_x", type=int, default=1920)
    ap.add_argument("--win_y", type=int, default=0)
    ap.add_argument("--csv", default="")
    args = ap.parse_args()

    with open(SHM, "rb") as fh:
        in_w, in_h, _, _ = struct.unpack("IIII", fh.read(HDR))

    import openvino as ov
    core = ov.Core()
    model = core.read_model(f"{MODELS}/FSRCNN_x{args.scale}.xml")
    model.reshape([1, in_h, in_w, 1])   # entrada NHWC al tamano de render
    comp = core.compile_model(model, "GPU", {"CACHE_DIR": "/tmp/openvino_cache"})
    req = comp.create_infer_request()

    if not args.no_display:
        cv2.namedWindow("salida", cv2.WINDOW_NORMAL)
        # En el 2o monitor: si tapa la ventana del juego, el compositor
        # Wayland congela sus swaps (throttling de Xwayland) y no hay frames.
        cv2.moveWindow("salida", args.win_x, args.win_y)
        cv2.resizeWindow("salida", args.out_w, args.out_h)

    stages = {k: [] for k in
              ("espera", "lectura", "preproceso", "inferencia",
               "postproceso", "presentacion", "total")}
    last_seq = 0
    n = 0
    f = open(SHM, "rb")
    while n < args.frames + args.warmup:
        tw = time.perf_counter()
        # --- espera: hasta que el juego produce un frame nuevo ---
        while True:
            f.seek(0)
            w, h, seq, ready = struct.unpack("IIII", f.read(HDR))
            if ready == 1 and (seq != last_seq or (args.stale_ok and n > 0)):
                break
            time.sleep(0.0005)
        last_seq = seq
        t0 = time.perf_counter()
        # --- lectura: copiar el frame desde shm ---
        f.seek(HDR)
        buf = f.read(w * h * 4)
        frame = np.frombuffer(buf, np.uint8).reshape((h, w, 4))
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        t1 = time.perf_counter()

        # --- preproceso: separar luminancia, normalizar, NHWC ---
        ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y = ycc[:, :, 0].astype(np.float32) / 255.0
        yin = y[None, :, :, None]
        t2 = time.perf_counter()

        # --- inferencia FSRCNN en la iGPU ---
        res = req.infer({0: yin})
        y_sr = np.squeeze(list(res.values())[0])
        t3 = time.perf_counter()

        # --- postproceso: croma bicubico + merge + tamano de salida ---
        y8 = np.clip(y_sr * 255.0, 0, 255).astype(np.uint8)
        crcb = cv2.resize(ycc[:, :, 1:], (y8.shape[1], y8.shape[0]),
                          interpolation=cv2.INTER_CUBIC)
        out = cv2.cvtColor(np.dstack((y8, crcb)), cv2.COLOR_YCrCb2BGR)
        if (out.shape[1], out.shape[0]) != (args.out_w, args.out_h):
            out = cv2.resize(out, (args.out_w, args.out_h),
                             interpolation=cv2.INTER_CUBIC)
        t4 = time.perf_counter()

        # --- presentacion ---
        if not args.no_display:
            cv2.imshow("salida", out)
            cv2.waitKey(1)
        t5 = time.perf_counter()

        n += 1
        if n <= args.warmup:
            continue
        stages["espera"].append((t0 - tw) * 1000)
        stages["lectura"].append((t1 - t0) * 1000)
        stages["preproceso"].append((t2 - t1) * 1000)
        stages["inferencia"].append((t3 - t2) * 1000)
        stages["postproceso"].append((t4 - t3) * 1000)
        stages["presentacion"].append((t5 - t4) * 1000)
        stages["total"].append((t5 - t0) * 1000)
    f.close()

    print(f"# render {w}x{h}, escala x{args.scale}, "
          f"salida {args.out_w}x{args.out_h}, "
          f"{args.frames} frames (tras {args.warmup} de calentamiento)")
    print(f"{'etapa':<14}{'media':>8}{'p50':>8}{'p90':>8}")
    rows = []
    for k, v in stages.items():
        a = np.array(v)
        print(f"{k:<14}{a.mean():>8.2f}{np.percentile(a, 50):>8.2f}"
              f"{np.percentile(a, 90):>8.2f}")
        rows.append((k, a.mean(), np.percentile(a, 50), np.percentile(a, 90)))
    if args.csv:
        with open(args.csv, "w") as fh:
            fh.write("etapa,media_ms,p50_ms,p90_ms\n")
            for k, m, p50, p90 in rows:
                fh.write(f"{k},{m:.3f},{p50:.3f},{p90:.3f}\n")


if __name__ == "__main__":
    main()
