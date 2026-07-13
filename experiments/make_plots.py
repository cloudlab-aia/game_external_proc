"""Genera las gráficas de los experimentos desde los CSV de results/experiments/.

Salidas en results/experiments/plots/:
  - crossover.png        : el cruce dGPU vs iGPU al saturar la dGPU (figura estrella)
  - sweep_x{2,3,4}.png   : FPS de inferencia vs resolución por dispositivo (Exp A)
  - load_matrix.png      : FPS por dispositivo y estado de carga (Exp B matriz)
"""
import csv
import os
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(REPO, "results", "experiments")
OUT = os.path.join(EXP, "plots")
os.makedirs(OUT, exist_ok=True)


def read(name):
    p = os.path.join(EXP, name)
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []


# ---- 1. CRUCE (figura estrella) ----
g = read("expB_gradient.csv")
if g:
    order = []
    util = {}
    fps = collections.defaultdict(dict)
    for r in g:
        lt = r["load_tag"]
        if lt not in order:
            order.append(lt)
            util[lt] = int(lt.split("util")[1])
        fps[r["device"]][lt] = float(r["fps_p50"])
    x = list(range(len(order)))   # nivel de carga (nº de procesos de stress)
    plt.figure(figsize=(8, 5))
    plt.plot(x, [fps["dGPU"][lt] for lt in order], "o-", color="#76b900", lw=2, label="dGPU (NVIDIA, CUDA)")
    plt.plot(x, [fps["iGPU"][lt] for lt in order], "s-", color="#0071c5", lw=2, label="iGPU (Intel, OpenVINO)")
    plt.xticks(x, [f"{util[lt]}%" for lt in order])
    plt.xlabel("Carga de la dGPU (utilización %), creciente →")
    plt.ylabel("FPS de inferencia FSRCNN x4 (480×270→1080p)")
    plt.title("Cruce de rendimiento: al saturar la dGPU, la iGPU la supera")
    plt.grid(alpha=0.3); plt.legend()
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "crossover.png"), dpi=130)
    plt.close()
    print("crossover.png OK")

# ---- 2. BARRIDO por escala (Exp A) ----
a = read("expA_inference_sweep.csv")
if a:
    colors = {"dGPU": "#76b900", "iGPU": "#0071c5", "CPU": "#e8a000"}
    for scale in ["2", "3", "4"]:
        plt.figure(figsize=(8, 5))
        for dev in ["dGPU", "iGPU", "CPU"]:
            pts = sorted([(int(r["in_w"]) * int(r["in_h"]), float(r["fps_p50"]))
                          for r in a if r["scale"] == scale and r["device"] == dev])
            if pts:
                xs = [p[0] / 1000 for p in pts]
                plt.plot(xs, [p[1] for p in pts], "o-", color=colors[dev], label=dev)
        plt.axhline(60, color="gray", ls="--", alpha=0.6, label="60 FPS")
        plt.xlabel("Píxeles de entrada (miles)")
        plt.ylabel("FPS de inferencia (p50)")
        plt.title(f"FSRCNN x{scale}: inferencia por dispositivo y resolución (sin carga)")
        plt.grid(alpha=0.3); plt.legend()
        plt.tight_layout(); plt.savefig(os.path.join(OUT, f"sweep_x{scale}.png"), dpi=130)
        plt.close()
    print("sweep_x2/3/4.png OK")

# ---- 3. MATRIZ DE CARGA (Exp B matriz) ----
m = read("expB_crossover.csv")
if m:
    loads = ["idle", "cpu", "igpu", "dgpu"]
    devs = ["dGPU", "iGPU", "CPU"]
    colors = {"dGPU": "#76b900", "iGPU": "#0071c5", "CPU": "#e8a000"}
    t = collections.defaultdict(dict)
    for r in m:
        t[r["device"]][r["load_tag"]] = float(r["fps_p50"])
    import numpy as np
    x = np.arange(len(loads)); w = 0.25
    plt.figure(figsize=(8, 5))
    for i, d in enumerate(devs):
        plt.bar(x + i * w, [t[d].get(l, 0) for l in loads], w, label=d, color=colors[d])
    plt.xticks(x + w, ["sin carga", "carga CPU", "carga iGPU", "carga dGPU"])
    plt.ylabel("FPS de inferencia (p50)")
    plt.title("Estabilidad bajo carga: la iGPU apenas se degrada")
    plt.legend(); plt.grid(axis="y", alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "load_matrix.png"), dpi=130)
    plt.close()
    print("load_matrix.png OK")

# ---- 4. Exp C: FPS del juego con shaders (nativa vs híbrida) ----
c = read("expC_shaders.csv")
if c:
    import numpy as np
    d = {r["config"]: (r["resolucion"], float(r["fps_render"])) for r in c}
    bars, labels, cols = [], [], []
    if "nativa" in d:
        bars.append(d["nativa"][1]); labels.append(f"Nativa\n(render 1080p)"); cols.append("#c0392b")
    if "IA_iGPU_hibrida" in d:
        bars.append(d["IA_iGPU_hibrida"][1]); labels.append(f"Híbrida\n(render {d['IA_iGPU_hibrida'][0]} + iGPU)"); cols.append("#27ae60")
    if "IA_dGPU_dedicada" in d:
        bars.append(d["IA_dGPU_dedicada"][1]); labels.append(f"Dedicada\n(render {d['IA_dGPU_dedicada'][0]} + dGPU)"); cols.append("#e8a000")
    if bars:
        plt.figure(figsize=(7, 5))
        x = np.arange(len(bars))
        b = plt.bar(x, bars, color=cols, width=0.6)
        for i, v in enumerate(bars):
            plt.text(i, v + 0.4, f"{v:.0f}", ha="center", fontweight="bold")
        plt.xticks(x, labels)
        plt.ylabel("FPS del juego (render)")
        plt.title("FPS con shaders Photon, misma salida 1080p")
        if "nativa" in d and "IA_iGPU_hibrida" in d and d["nativa"][1] > 0:
            r = d["IA_iGPU_hibrida"][1] / d["nativa"][1]
            plt.text(0.5, max(bars) * 0.85, f"híbrida {r:.1f}× nativa", ha="center",
                     fontsize=12, bbox=dict(boxstyle="round", fc="#eafaf1"))
        plt.grid(axis="y", alpha=0.3)
        plt.tight_layout(); plt.savefig(os.path.join(OUT, "expC_shaders.png"), dpi=130)
        plt.close()
        print("expC_shaders.png OK")

print("Gráficas en", OUT)
