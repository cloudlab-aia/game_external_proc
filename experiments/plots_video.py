#!/usr/bin/env python3
"""Genera las graficas de resultados para el video del TFG, limpias y en
alta resolucion (fondo blanco, fuentes grandes, paleta coherente).

Salida: ~/Desktop/video_tfg/entrega_editor/graficas/
  1. inferencia_dgpu_vs_igpu.png  (modelos optimizados)
  2. sistema_x2.png / x3 / x4      (dedicada vs hibrida vs nativa)
  3. latencia_componentes.png      (desglose de 35 ms)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "results", "experiments")
OUT = os.path.expanduser("~/Desktop/video_tfg/entrega_editor/graficas")
os.makedirs(OUT, exist_ok=True)

# --- estilo global, pensado para verse bien en video ---
plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.size": 15,
    "axes.titlesize": 19,
    "axes.labelsize": 16,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "legend.fontsize": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "font.family": "DejaVu Sans",
})
C_DGPU = "#4E79A7"     # dedicada / dGPU  -> azul
C_IGPU = "#E15759"     # hibrida / iGPU   -> rojo coral (protagonista)
C_NAT = "#8C8C8C"      # nativa           -> gris
C_LIM = "#59A14F"      # linea limite     -> verde


def load(fn):
    with open(os.path.join(RES, fn)) as f:
        return list(csv.DictReader(f))


# ============================================================
# 1) INFERENCIA dGPU vs iGPU  (FSRCNN optimizado: ORT:CUDA / OV:GPU)
# ============================================================
def grafica_inferencia():
    rows = load("expA_inference_sweep.csv")
    scale = "3"
    dg, ig, xs = [], [], []
    seen = []
    for r in rows:
        if r["scale"] != scale or r["load_tag"] != "idle":
            continue
    # recopilar por resolucion de entrada, dGPU e iGPU
    byres = {}
    for r in rows:
        if r["scale"] != scale or r["load_tag"] != "idle":
            continue
        key = f'{r["in_w"]}x{r["in_h"]}'
        byres.setdefault(key, {})[r["device"]] = float(r["mean_ms"])
    order = sorted(byres, key=lambda k: int(k.split("x")[0]))
    xs = order
    dg = [byres[k].get("dGPU", np.nan) for k in order]
    ig = [byres[k].get("iGPU", np.nan) for k in order]

    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    x = np.arange(len(xs))
    ax.plot(x, dg, "-o", color=C_DGPU, lw=3, ms=9, label="dGPU (ONNX Runtime + CUDA)")
    ax.plot(x, ig, "-o", color=C_IGPU, lw=3, ms=9, label="iGPU (OpenVINO)")
    ax.axhline(33.3, color=C_LIM, lw=2, ls="--")
    ax.text(0.2, 34.8, "Límite tiempo real (30 FPS)", color=C_LIM, fontsize=12.5, fontweight="bold")

    for xi, v in zip(x, ig):
        ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=11, color=C_IGPU)
    for xi, v in zip(x, dg):
        ax.annotate(f"{v:.1f}", (xi, v), textcoords="offset points",
                    xytext=(0, -16), ha="center", fontsize=11, color=C_DGPU)

    ax.set_xticks(x)
    ax.set_xticklabels(xs)
    ax.set_xlabel("Resolución de entrada (píxeles)")
    ax.set_ylabel("Tiempo de inferencia (ms)")
    ax.set_title("Inferencia FSRCNN ×3 optimizado: dGPU frente a iGPU", fontweight="bold")
    ax.legend(loc="upper left", frameon=False)
    ax.set_ylim(0, max(max(dg), max(ig)) * 1.18)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "1_inferencia_dgpu_vs_igpu.png"), facecolor="white")
    plt.close(fig)
    print("  1_inferencia_dgpu_vs_igpu.png")


# ============================================================
# 2) SISTEMA: dedicada vs hibrida vs nativa  (x2, x3, x4)
# ============================================================
def grafica_sistema():
    rows = load("expG_resolution_xvfb_skip.csv")
    nat = load("expG_native_output.csv")
    native_by_w = {}
    for r in nat:
        w = int(r["output_res"].split("x")[0])
        native_by_w[w] = float(r["game_fps"])

    def nearest_native(w):
        k = min(native_by_w, key=lambda kk: abs(kk - w))
        return native_by_w[k]

    for scale in ("2", "3", "4"):
        sub = [r for r in rows if r["scale"] == scale]
        inputs = sorted({r["input_res"] for r in sub},
                        key=lambda k: int(k.split("x")[0]))
        ded, hyb, natl = [], [], []
        for res in inputs:
            iw = int(res.split("x")[0])
            ow = iw * int(scale)
            d = next((r for r in sub if r["input_res"] == res and r["device"] == "dGPU"), None)
            h = next((r for r in sub if r["input_res"] == res and r["device"] == "iGPU"), None)
            ded.append(float(d["game_fps"]) if d else np.nan)
            hyb.append(float(h["game_fps"]) if h else np.nan)
            natl.append(nearest_native(ow))

        fig, ax = plt.subplots(figsize=(9.5, 5.6))
        x = np.arange(len(inputs))
        ax.plot(x, hyb, "-o", color=C_IGPU, lw=3.2, ms=10, label="Híbrida (IA en iGPU)", zorder=3)
        ax.plot(x, ded, "-o", color=C_DGPU, lw=3, ms=9, label="Dedicada (IA en dGPU)", zorder=2)
        ax.plot(x, natl, "--s", color=C_NAT, lw=2.5, ms=8, label="Nativa (render a la salida)", zorder=1)

        ax.fill_between(x, ded, hyb, where=[h >= d for h, d in zip(hyb, ded)],
                        color=C_IGPU, alpha=0.08, zorder=0)

        ax.set_xticks(x)
        ax.set_xticklabels(inputs)
        ax.set_xlabel("Resolución de render (entrada)")
        ax.set_ylabel("FPS de render del juego")
        ax.set_title(f"Rendimiento del sistema — escala ×{scale}", fontweight="bold")
        ax.legend(loc="lower left", frameon=False)
        ax.set_ylim(0, 70)
        fig.tight_layout()
        fn = f"2_sistema_x{scale}.png"
        fig.savefig(os.path.join(OUT, fn), facecolor="white")
        plt.close(fig)
        print(f"  {fn}")


# ============================================================
# 3) LATENCIA POR COMPONENTE  (barra horizontal apilada, 35 ms)
# ============================================================
def grafica_latencia():
    rows = load("latency_components.csv")
    etapas = {r["etapa"]: float(r["media_ms"]) for r in rows}
    orden = ["espera", "lectura", "preproceso", "inferencia", "postproceso", "presentacion"]
    nombres = {
        "espera": "Espera", "lectura": "Lectura", "preproceso": "Preproceso",
        "inferencia": "Inferencia (iGPU)", "postproceso": "Postproceso (CPU)",
        "presentacion": "Presentación",
    }
    colores = {
        "espera": "#BAB0AC", "lectura": "#BAB0AC", "preproceso": "#BAB0AC",
        "inferencia": C_IGPU, "postproceso": "#F28E2B", "presentacion": "#76B7B2",
    }
    fig, ax = plt.subplots(figsize=(10.5, 3.2))
    left = 0
    total = etapas["total"]
    for e in orden:
        v = etapas[e]
        ax.barh(0, v, left=left, color=colores[e], edgecolor="white", height=0.6)
        if v > 1.5:
            ax.text(left + v / 2, 0, f"{nombres[e]}\n{v:.1f} ms", ha="center",
                    va="center", fontsize=11.5, color="white", fontweight="bold")
        left += v
    ax.text(total, 0.42, f"Total  {total:.1f} ms", ha="right", va="bottom",
            fontsize=14, fontweight="bold", color="#333")
    ax.set_xlim(0, total * 1.02)
    ax.set_ylim(-0.5, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("Tiempo por frame (ms)")
    ax.set_title("Latencia por componente del pipeline (640×360, FSRCNN ×3, iGPU)",
                 fontweight="bold", fontsize=17)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "3_latencia_componentes.png"), facecolor="white")
    plt.close(fig)
    print("  3_latencia_componentes.png")


if __name__ == "__main__":
    print("Generando graficas en", OUT)
    grafica_inferencia()
    grafica_sistema()
    grafica_latencia()
    print("Listo.")
