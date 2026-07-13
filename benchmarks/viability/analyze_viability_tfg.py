#!/usr/bin/env python3
"""
analyze_viability_tfg.py

Análisis extendido para documentación TFG.
Genera todos los plots y tablas de viabilidad en results/plots_tfg/.

Plots generados:
 01_latency_vs_resolution_{model}_{device}.png - curva latencia vs res por load
 02_heatmap_interference.png - degradación % heatmap
 03_fps_bar_idle.png - FPS por device×model idle
 04_fps_grouped_load.png - FPS a res canónica por load state
 05_fsrcnn_scale_comparison_{device}.png - x2/x3/x4 en mismo device
 06_heatmap_fps_idle.png - device×model throughput heatmap
 07_boxplot_by_device.png - box plot latencia por device
 08_cdf_latency.png - CDF p50 latencia por device
 09_bar_degradation.png - barras % degradación
 10_scatter_pixels_fps.png - scatter pixels vs FPS
 11_bar_best_device_per_model.png - mejor device por modelo

CSV adicionales:
 ranking_idle.csv - ranking de devices por p50 idle (por modelo×res)
 full_stats.csv - todas las métricas extendidas por celda
"""

import os
import sys
import csv
import math
from pathlib import Path
from collections import defaultdict
import numpy as np

try:
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 import matplotlib.ticker as ticker
 HAS_MPL = True
except ImportError:
 print("[!] matplotlib no disponible", file=sys.stderr)
 HAS_MPL = False

RESULTS_CSV = Path(__file__).parent / "results" / "viability_results.csv"
OUT_DIR = Path(__file__).parent / "results" / "plots_tfg"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEVICE_ORDER = ["CPU_OCV", "CPU_OV", "iGPU_OCL", "iGPU_OV", "dGPU_OCL", "dGPU_CUDA"]
LOAD_ORDER = ["idle", "cpu", "igpu", "dgpu"]
LOAD_COLORS = {"idle": "#2196F3", "cpu": "#FF9800", "igpu": "#4CAF50", "dgpu": "#F44336"}
LOAD_MARKERS = {"idle": "o", "cpu": "s", "igpu": "^", "dgpu": "D"}
DEVICE_COLORS = {
 "CPU_OCV": "#607D8B",
 "CPU_OV": "#9C27B0",
 "iGPU_OCL": "#2196F3",
 "iGPU_OV": "#00BCD4",
 "dGPU_OCL": "#FF5722",
 "dGPU_CUDA":"#F44336",
}

# Resolución canónica de referencia para comparativas entre devices
CANONICAL_W, CANONICAL_H = 320, 180 # 320×180 está en casi todos los models


def load_rows():
 rows = []
 with open(RESULTS_CSV, newline="", encoding="utf-8") as cf:
 for row in csv.DictReader(cf):
 try:
 row["input_w"] = int(row["input_w"])
 row["input_h"] = int(row["input_h"])
 row["mean_ms"] = float(row["mean_ms"])
 row["p50_ms"] = float(row["p50_ms"])
 row["p90_ms"] = float(row["p90_ms"])
 row["p99_ms"] = float(row["p99_ms"])
 row["fps_p50"] = float(row["fps_p50"])
 row["fps_mean"] = float(row["fps_mean"])
 row["pixels"] = row["input_w"] * row["input_h"]
 except (KeyError, ValueError):
 continue
 rows.append(row)
 return rows


def save(fig, name, dpi=130):
 path = OUT_DIR / name
 fig.tight_layout()
 fig.savefig(path, dpi=dpi, bbox_inches="tight")
 plt.close(fig)
 print(f"[OK] {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 01 Latencia vs resolución (una gráfica por model×device, curva por load)
# ─────────────────────────────────────────────────────────────────────────────
def plot_latency_vs_resolution(rows):
 by_md = defaultdict(list)
 for r in rows:
 by_md[(r["model"], r["device"])].append(r)

 for (model, device), lst in by_md.items():
 by_load = defaultdict(list)
 for r in lst:
 by_load[r["load_tag"]].append(r)

 fig, ax = plt.subplots(figsize=(8, 5))
 plotted = False
 for load in LOAD_ORDER:
 rs = by_load.get(load, [])
 if not rs:
 continue
 rs = sorted(rs, key=lambda x: x["pixels"])
 xs = [r["pixels"] / 1000 for r in rs]
 ys = [r["p50_ms"] for r in rs]
 ax.plot(xs, ys,
 marker=LOAD_MARKERS[load], color=LOAD_COLORS[load],
 label=f"load={load}", linewidth=1.8, markersize=5)
 plotted = True

 if not plotted:
 plt.close(fig)
 continue

 ax.set_xlabel("Kpíxeles de entrada")
 ax.set_ylabel("Latencia p50 (ms)")
 ax.set_title(f"{model} @ {device}")
 ax.grid(True, alpha=0.3)
 ax.legend(fontsize=9)

 all_x = [r["pixels"] / 1000 for r in lst]
 if len(all_x) > 1 and max(all_x) > 0 and max(all_x) / max(min(all_x), 1) > 50:
 ax.set_xscale("log")
 ax.set_yscale("log")

 fname = f"01_latency_vs_resolution_{model.replace('.','_')}_{device}.png"
 save(fig, fname)


# ─────────────────────────────────────────────────────────────────────────────
# 02 Heatmap de interferencia relativa
# ─────────────────────────────────────────────────────────────────────────────
def plot_heatmap_interference(rows):
 key2p50 = {}
 for r in rows:
 k = (r["device"], r["model"], r["input_w"], r["input_h"], r["load_tag"])
 key2p50[k] = r["p50_ms"]

 agg = defaultdict(list)
 for (dev, m, w, h, load), val in key2p50.items():
 if load == "idle":
 continue
 idle = key2p50.get((dev, m, w, h, "idle"))
 if idle and idle > 0:
 agg[(dev, load)].append((val - idle) / idle * 100.0)

 devs = [d for d in DEVICE_ORDER if any(k[0] == d for k in agg)]
 loads = [L for L in LOAD_ORDER if L != "idle" and any(k[1] == L for k in agg)]
 if not devs or not loads:
 return

 M = np.full((len(devs), len(loads)), np.nan)
 for i, d in enumerate(devs):
 for j, L in enumerate(loads):
 lst = agg.get((d, L))
 if lst:
 M[i, j] = float(np.mean(lst))

 fig, ax = plt.subplots(figsize=(max(6, len(loads)*2), max(4, len(devs)*0.8)))
 im = ax.imshow(M, cmap="RdYlGn_r", vmin=-10, vmax=80, aspect="auto")
 ax.set_xticks(range(len(loads)))
 ax.set_xticklabels([f"load={L}" for L in loads])
 ax.set_yticks(range(len(devs)))
 ax.set_yticklabels(devs)
 for i in range(len(devs)):
 for j in range(len(loads)):
 v = M[i, j]
 if not np.isnan(v):
 ax.text(j, i, f"{v:+.0f}%", ha="center", va="center",
 color="white" if abs(v) > 35 else "black", fontsize=10, fontweight="bold")
 ax.set_title("Interferencia media relativa por dispositivo y tipo de carga\n"
 "(p50_load − p50_idle) / p50_idle × 100")
 fig.colorbar(im, ax=ax, label="% degradación")
 save(fig, "02_heatmap_interference.png")


# ─────────────────────────────────────────────────────────────────────────────
# 03 FPS bar chart (idle, todos los devices y modelos a res canónica)
# ─────────────────────────────────────────────────────────────────────────────
def _nearest_res(lst, target_pixels):
 """Devuelve el subconjunto de rows con resolución más cercana al target."""
 if not lst:
 return []
 best_px = min((r["pixels"] for r in lst), key=lambda px: abs(px - target_pixels))
 return [r for r in lst if r["pixels"] == best_px]


def plot_fps_bar_idle(rows):
 target = CANONICAL_W * CANONICAL_H
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_dm = defaultdict(list)
 for r in idle_rows:
 by_dm[(r["device"], r["model"])].append(r)

 entries = []
 for (dev, model), lst in by_dm.items():
 near = _nearest_res(lst, target)
 if near:
 best = max(near, key=lambda x: x["fps_p50"]) # toma la mejor iteración
 entries.append((dev, model, best["fps_p50"], best["input_w"], best["input_h"]))

 if not entries:
 return

 entries.sort(key=lambda e: (DEVICE_ORDER.index(e[0]) if e[0] in DEVICE_ORDER else 99,
 e[1]))

 labels = [f"{e[0]}\n{e[1].replace('.onnx','').replace('.pb','').replace('.xml','')}"
 for e in entries]
 vals = [e[2] for e in entries]
 colors = [DEVICE_COLORS.get(e[0], "gray") for e in entries]

 fig, ax = plt.subplots(figsize=(max(10, len(entries)*0.8), 5))
 bars = ax.bar(range(len(entries)), vals, color=colors, edgecolor="white", linewidth=0.5)
 ax.set_xticks(range(len(entries)))
 ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
 ax.set_ylabel("FPS (p50, idle)")
 ax.set_title(f"Throughput por dispositivo×modelo (resolución ≈ {CANONICAL_W}×{CANONICAL_H}, sin carga)")
 ax.grid(axis="y", alpha=0.3)
 for bar, v in zip(bars, vals):
 if v > 0:
 ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.01,
 f"{v:.0f}", ha="center", va="bottom", fontsize=7)
 save(fig, "03_fps_bar_idle.png")


# ─────────────────────────────────────────────────────────────────────────────
# 04 FPS agrupado por load state (res canónica)
# ─────────────────────────────────────────────────────────────────────────────
def plot_fps_grouped_load(rows):
 target = CANONICAL_W * CANONICAL_H
 by_dml = defaultdict(list)
 for r in rows:
 by_dml[(r["device"], r["model"], r["load_tag"])].append(r)

 combos = set()
 for (d, m, _) in by_dml:
 combos.add((d, m))
 combos = sorted(combos, key=lambda x: (
 DEVICE_ORDER.index(x[0]) if x[0] in DEVICE_ORDER else 99, x[1]))

 loads_present = [L for L in LOAD_ORDER if
 any(r["load_tag"] == L for r in rows)]

 n_combos = len(combos)
 n_loads = len(loads_present)
 if n_combos == 0:
 return

 width = 0.8 / n_loads
 x = np.arange(n_combos)

 fig, ax = plt.subplots(figsize=(max(12, n_combos * 0.6), 5))
 for li, load in enumerate(loads_present):
 fps_vals = []
 for (dev, model) in combos:
 lst = _nearest_res(by_dml.get((dev, model, load), []), target)
 if lst:
 fps_vals.append(max(r["fps_p50"] for r in lst))
 else:
 fps_vals.append(0.0)
 offset = (li - n_loads / 2 + 0.5) * width
 ax.bar(x + offset, fps_vals, width=width * 0.9,
 label=f"load={load}", color=LOAD_COLORS[load], edgecolor="white")

 labels = [f"{d}\n{m.replace('.onnx','').replace('.pb','').replace('.xml','')}"
 for d, m in combos]
 ax.set_xticks(x)
 ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=7)
 ax.set_ylabel("FPS (p50)")
 ax.set_title(f"FPS por dispositivo×modelo y estado de carga (resolución ≈ {CANONICAL_W}×{CANONICAL_H})")
 ax.legend(fontsize=9)
 ax.grid(axis="y", alpha=0.3)
 save(fig, "04_fps_grouped_load.png")


# ─────────────────────────────────────────────────────────────────────────────
# 05 FSRCNN: comparativa factor de escala x2/x3/x4 por device
# ─────────────────────────────────────────────────────────────────────────────
def plot_fsrcnn_scale_comparison(rows):
 fsrcnn_rows = [r for r in rows
 if r["model"].startswith("FSRCNN") and r["load_tag"] == "idle"]
 by_device = defaultdict(list)
 for r in fsrcnn_rows:
 by_device[r["device"]].append(r)

 scale_colors = {"FSRCNN_x2.pb": "#2196F3", "FSRCNN_x3.pb": "#4CAF50", "FSRCNN_x4.pb": "#F44336"}

 for device, lst in by_device.items():
 by_model = defaultdict(list)
 for r in lst:
 by_model[r["model"]].append(r)

 fig, ax = plt.subplots(figsize=(8, 5))
 plotted = False
 for model in ["FSRCNN_x2.pb", "FSRCNN_x3.pb", "FSRCNN_x4.pb"]:
 rs = sorted(by_model.get(model, []), key=lambda x: x["pixels"])
 if not rs:
 continue
 xs = [r["pixels"] / 1000 for r in rs]
 ys = [r["p50_ms"] for r in rs]
 scale = model.split("_x")[1].replace(".pb", "")
 ax.plot(xs, ys, marker="o", color=scale_colors[model],
 label=f"×{scale}", linewidth=1.8, markersize=5)
 plotted = True

 if not plotted:
 plt.close(fig)
 continue

 ax.set_xlabel("Kpíxeles de entrada")
 ax.set_ylabel("Latencia p50 (ms)")
 ax.set_title(f"FSRCNN: factor de escala vs latencia @ {device} (idle)")
 ax.grid(True, alpha=0.3)
 ax.legend(title="Factor escala", fontsize=10)
 save(fig, f"05_fsrcnn_scale_{device}.png")


# ─────────────────────────────────────────────────────────────────────────────
# 06 Heatmap FPS idle: device × model (a resolución canónica)
# ─────────────────────────────────────────────────────────────────────────────
def plot_heatmap_fps_idle(rows):
 target = CANONICAL_W * CANONICAL_H
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_dm = defaultdict(list)
 for r in idle_rows:
 by_dm[(r["device"], r["model"])].append(r)

 devs = [d for d in DEVICE_ORDER if any(k[0] == d for k in by_dm)]
 models = sorted({k[1] for k in by_dm})
 if not devs or not models:
 return

 M = np.full((len(devs), len(models)), np.nan)
 for i, d in enumerate(devs):
 for j, m in enumerate(models):
 lst = _nearest_res(by_dm.get((d, m), []), target)
 if lst:
 M[i, j] = float(max(r["fps_p50"] for r in lst))

 fig, ax = plt.subplots(figsize=(max(8, len(models)*1.5), max(4, len(devs)*0.9)))
 im = ax.imshow(M, cmap="YlOrRd", aspect="auto")
 ax.set_xticks(range(len(models)))
 ax.set_xticklabels([m.replace(".onnx","").replace(".pb","").replace(".xml","")
 for m in models], rotation=30, ha="right", fontsize=9)
 ax.set_yticks(range(len(devs)))
 ax.set_yticklabels(devs)
 for i in range(len(devs)):
 for j in range(len(models)):
 v = M[i, j]
 if not np.isnan(v):
 ax.text(j, i, f"{v:.0f}", ha="center", va="center",
 color="black" if v < np.nanmax(M) * 0.7 else "white",
 fontsize=9, fontweight="bold")
 ax.set_title(f"FPS p50 (idle) por dispositivo × modelo\n(resolución ≈ {CANONICAL_W}×{CANONICAL_H})")
 fig.colorbar(im, ax=ax, label="FPS (p50)")
 save(fig, "06_heatmap_fps_idle.png")


# ─────────────────────────────────────────────────────────────────────────────
# 07 Box plot latencia por device (todas las resoluciones, load=idle)
# ─────────────────────────────────────────────────────────────────────────────
def plot_boxplot_by_device(rows):
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_device = defaultdict(list)
 for r in idle_rows:
 by_device[r["device"]].append(r["p50_ms"])

 devs = [d for d in DEVICE_ORDER if d in by_device]
 if not devs:
 return

 data = [by_device[d] for d in devs]
 fig, ax = plt.subplots(figsize=(10, 5))
 bp = ax.boxplot(data, patch_artist=True, notch=False,
 medianprops=dict(color="black", linewidth=2))
 for patch, dev in zip(bp["boxes"], devs):
 patch.set_facecolor(DEVICE_COLORS.get(dev, "gray"))
 patch.set_alpha(0.7)

 ax.set_xticks(range(1, len(devs)+1))
 ax.set_xticklabels(devs, rotation=20, ha="right")
 ax.set_ylabel("Latencia p50 (ms)")
 ax.set_title("Distribución de latencia p50 por dispositivo (idle, todas las resoluciones)")
 ax.set_yscale("log")
 ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
 ax.grid(axis="y", alpha=0.3)
 save(fig, "07_boxplot_by_device.png")


# ─────────────────────────────────────────────────────────────────────────────
# 08 CDF de latencia p50 por device
# ─────────────────────────────────────────────────────────────────────────────
def plot_cdf(rows):
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_device = defaultdict(list)
 for r in idle_rows:
 by_device[r["device"]].append(r["p50_ms"])

 devs = [d for d in DEVICE_ORDER if d in by_device]
 if not devs:
 return

 fig, ax = plt.subplots(figsize=(9, 5))
 for dev in devs:
 vals = sorted(by_device[dev])
 cdf = np.arange(1, len(vals)+1) / len(vals)
 ax.plot(vals, cdf, label=dev, color=DEVICE_COLORS.get(dev, "gray"), linewidth=2)

 ax.set_xlabel("Latencia p50 (ms)")
 ax.set_ylabel("CDF")
 ax.set_title("CDF de latencia p50 por dispositivo (idle)")
 ax.set_xscale("log")
 ax.legend(fontsize=9)
 ax.grid(True, alpha=0.3)
 ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
 save(fig, "08_cdf_latency.png")


# ─────────────────────────────────────────────────────────────────────────────
# 09 Barras % degradación por (device, load)
# ─────────────────────────────────────────────────────────────────────────────
def plot_degradation_bars(rows):
 key2p50 = {}
 for r in rows:
 k = (r["device"], r["model"], r["input_w"], r["input_h"], r["load_tag"])
 key2p50[k] = r["p50_ms"]

 agg = defaultdict(list)
 for (dev, m, w, h, load), val in key2p50.items():
 if load == "idle":
 continue
 idle = key2p50.get((dev, m, w, h, "idle"))
 if idle and idle > 0:
 agg[(dev, load)].append((val - idle) / idle * 100.0)

 devs = [d for d in DEVICE_ORDER if any(k[0] == d for k in agg)]
 loads = [L for L in LOAD_ORDER if L != "idle" and any(k[1] == L for k in agg)]
 if not devs or not loads:
 return

 n_devs = len(devs)
 n_loads = len(loads)
 x = np.arange(n_devs)
 width = 0.8 / n_loads

 fig, ax = plt.subplots(figsize=(max(9, n_devs * 1.2), 5))
 for li, load in enumerate(loads):
 means = []
 errs = []
 for dev in devs:
 lst = agg.get((dev, load), [])
 means.append(float(np.mean(lst)) if lst else 0.0)
 errs.append(float(np.std(lst)) if lst else 0.0)
 offset = (li - n_loads/2 + 0.5) * width
 ax.bar(x + offset, means, width*0.9, yerr=errs, capsize=3,
 label=f"load={load}", color=LOAD_COLORS[load], alpha=0.85)

 ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
 ax.set_xticks(x)
 ax.set_xticklabels(devs, rotation=15, ha="right")
 ax.set_ylabel("Degradación media ± σ (%)")
 ax.set_title("Impacto de la carga del sistema en la latencia de inferencia\n"
 "(p50_load − p50_idle) / p50_idle × 100")
 ax.legend(fontsize=9)
 ax.grid(axis="y", alpha=0.3)
 save(fig, "09_bar_degradation.png")


# ─────────────────────────────────────────────────────────────────────────────
# 10 Scatter: píxeles de entrada vs FPS, coloreado por device
# ─────────────────────────────────────────────────────────────────────────────
def plot_scatter_pixels_fps(rows):
 idle_rows = [r for r in rows if r["load_tag"] == "idle" and r["fps_p50"] > 0]
 by_device = defaultdict(list)
 for r in idle_rows:
 by_device[r["device"]].append(r)

 devs = [d for d in DEVICE_ORDER if d in by_device]
 if not devs:
 return

 fig, ax = plt.subplots(figsize=(9, 5))
 for dev in devs:
 lst = by_device[dev]
 xs = [r["pixels"] / 1000 for r in lst]
 ys = [r["fps_p50"] for r in lst]
 ax.scatter(xs, ys, label=dev, color=DEVICE_COLORS.get(dev, "gray"),
 alpha=0.7, s=40, edgecolors="none")

 ax.set_xlabel("Kpíxeles de entrada")
 ax.set_ylabel("FPS (p50, idle)")
 ax.set_title("Throughput vs resolución de entrada por dispositivo (idle)")
 ax.set_xscale("log")
 ax.set_yscale("log")
 ax.legend(fontsize=9)
 ax.grid(True, alpha=0.2)
 ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
 ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
 save(fig, "10_scatter_pixels_fps.png")


# ─────────────────────────────────────────────────────────────────────────────
# 11 Mejor device por modelo a res canónica
# ─────────────────────────────────────────────────────────────────────────────
def plot_best_device_per_model(rows):
 target = CANONICAL_W * CANONICAL_H
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_dm = defaultdict(list)
 for r in idle_rows:
 by_dm[(r["device"], r["model"])].append(r)

 models = sorted({k[1] for k in by_dm})
 best_fps = {}
 best_dev = {}
 best_p50 = {}
 for m in models:
 top_fps, top_dev, top_p50 = 0.0, "", 0.0
 for d in DEVICE_ORDER:
 lst = _nearest_res(by_dm.get((d, m), []), target)
 if not lst:
 continue
 fps = max(r["fps_p50"] for r in lst)
 if fps > top_fps:
 top_fps = fps
 top_dev = d
 top_p50 = min(r["p50_ms"] for r in lst)
 if top_dev:
 best_fps[m] = top_fps
 best_dev[m] = top_dev
 best_p50[m] = top_p50

 if not best_fps:
 return

 sorted_models = sorted(best_fps, key=lambda m: best_fps[m], reverse=True)
 colors = [DEVICE_COLORS.get(best_dev[m], "gray") for m in sorted_models]
 vals = [best_fps[m] for m in sorted_models]
 labels = [m.replace(".onnx","").replace(".pb","").replace(".xml","")
 for m in sorted_models]

 fig, ax = plt.subplots(figsize=(max(8, len(sorted_models)*1.5), 5))
 bars = ax.bar(range(len(sorted_models)), vals, color=colors, edgecolor="white")
 for bar, m, v in zip(bars, sorted_models, vals):
 ax.text(bar.get_x() + bar.get_width()/2,
 bar.get_height() + max(vals)*0.01,
 f"{best_dev[m]}\n{v:.0f} FPS",
 ha="center", va="bottom", fontsize=7)

 ax.set_xticks(range(len(sorted_models)))
 ax.set_xticklabels(labels, rotation=25, ha="right")
 ax.set_ylabel("FPS máximo (p50, idle)")
 ax.set_title(f"Mejor dispositivo por modelo (resolución ≈ {CANONICAL_W}×{CANONICAL_H})")
 ax.grid(axis="y", alpha=0.3)

 # Leyenda de colores
 from matplotlib.patches import Patch
 legend_elements = [Patch(facecolor=DEVICE_COLORS.get(d, "gray"), label=d)
 for d in DEVICE_ORDER if d in {best_dev[m] for m in models}]
 ax.legend(handles=legend_elements, fontsize=8, loc="upper right")
 save(fig, "11_bar_best_device_per_model.png")


# ─────────────────────────────────────────────────────────────────────────────
# CSV: ranking_idle.csv
# ─────────────────────────────────────────────────────────────────────────────
def write_ranking(rows):
 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_mr = defaultdict(list)
 for r in idle_rows:
 by_mr[(r["model"], r["input_w"], r["input_h"])].append(r)

 out_path = Path(__file__).parent / "results" / "ranking_idle.csv"
 with open(out_path, "w", newline="", encoding="utf-8") as cf:
 w = csv.writer(cf)
 w.writerow(["model", "input_w", "input_h", "rank",
 "device", "p50_ms", "fps_p50"])
 for (model, iw, ih), lst in sorted(by_mr.items()):
 ranked = sorted(lst, key=lambda x: x["p50_ms"])
 for rank, r in enumerate(ranked, 1):
 w.writerow([model, iw, ih, rank, r["device"],
 r["p50_ms"], r["fps_p50"]])
 print(f"[OK] {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CSV: full_stats.csv (todas las métricas)
# ─────────────────────────────────────────────────────────────────────────────
def write_full_stats(rows):
 # Añade columnas derivadas útiles para TFG
 key2p50_idle = {}
 for r in rows:
 if r["load_tag"] == "idle":
 key2p50_idle[(r["device"], r["model"], r["input_w"], r["input_h"])] = r["p50_ms"]

 out_path = Path(__file__).parent / "results" / "full_stats.csv"
 with open(out_path, "w", newline="", encoding="utf-8") as cf:
 w = csv.writer(cf)
 w.writerow([
 "device", "model", "input_w", "input_h", "load_tag",
 "p50_ms", "p90_ms", "p99_ms", "mean_ms", "fps_p50",
 "degradation_pct", # vs idle, vacío si load=idle
 "viable_30fps", # p50 < 33.3 ms
 "viable_60fps", # p50 < 16.7 ms
 ])
 for r in rows:
 base_p50 = key2p50_idle.get(
 (r["device"], r["model"], r["input_w"], r["input_h"]))
 if base_p50 and base_p50 > 0 and r["load_tag"] != "idle":
 deg = round((r["p50_ms"] - base_p50) / base_p50 * 100.0, 2)
 else:
 deg = ""
 w.writerow([
 r["device"], r["model"], r["input_w"], r["input_h"], r["load_tag"],
 r["p50_ms"], r["p90_ms"], r["p99_ms"], r["mean_ms"], r["fps_p50"],
 deg,
 "SI" if r["p50_ms"] < 33.3 else "NO",
 "SI" if r["p50_ms"] < 16.7 else "NO",
 ])
 print(f"[OK] {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 12 PSNR / SSIM por modelo (quality_results.csv)
# ─────────────────────────────────────────────────────────────────────────────
def plot_quality_metrics():
 import csv as _csv
 qpath = Path(__file__).parent / "results" / "quality_results.csv"
 if not qpath.exists():
 print(f"[!] {qpath} no encontrado, saltando plot de calidad", file=sys.stderr)
 return

 rows = []
 with open(qpath, newline="", encoding="utf-8") as f:
 for r in _csv.DictReader(f):
 try:
 rows.append({
 "model": r["model"],
 "device": r["device"],
 "psnr": float(r["psnr_vs_bicubic"]),
 "ssim": float(r["ssim_vs_bicubic"]),
 "pixels": int(r["input_w"]) * int(r["input_h"]),
 "iw": int(r["input_w"]), "ih": int(r["input_h"]),
 })
 except (KeyError, ValueError):
 continue

 if not rows:
 return

 # ── 12a: PSNR medio por modelo (bar chart) ──
 from collections import defaultdict
 by_model = defaultdict(list)
 for r in rows:
 by_model[r["model"]].append(r["psnr"])

 models_sorted = sorted(by_model, key=lambda m: -float(np.mean(by_model[m])))
 labels = [m.replace(".onnx","").replace(".pb","").replace(".xml","") for m in models_sorted]
 means = [float(np.mean(by_model[m])) for m in models_sorted]
 stds = [float(np.std(by_model[m])) for m in models_sorted]

 fig, ax = plt.subplots(figsize=(max(8, len(models_sorted)*1.4), 5))
 bars = ax.bar(range(len(models_sorted)), means, yerr=stds, capsize=4,
 color=[DEVICE_COLORS.get("CPU_OV", "#607D8B")] * len(models_sorted),
 edgecolor="white", alpha=0.85)
 for bar, v in zip(bars, means):
 ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(stds)*0.3 + 0.3,
 f"{v:.1f} dB", ha="center", va="bottom", fontsize=9)
 ax.axhline(40, color="green", linestyle="--", linewidth=1, label="40 dB (referencia buena)")
 ax.axhline(30, color="orange", linestyle="--", linewidth=1, label="30 dB (referencia aceptable)")
 ax.set_xticks(range(len(models_sorted)))
 ax.set_xticklabels(labels, rotation=20, ha="right")
 ax.set_ylabel("PSNR vs bicubic (dB)")
 ax.set_title("Calidad de superresolución por modelo\n(PSNR medio ± σ vs interpolación bicúbica, frame tipo-juego)")
 ax.legend(fontsize=9)
 ax.grid(axis="y", alpha=0.3)
 save(fig, "12a_psnr_by_model.png")

 # ── 12b: SSIM medio por modelo ──
 by_model_ssim = defaultdict(list)
 for r in rows:
 by_model_ssim[r["model"]].append(r["ssim"])

 ssim_means = [float(np.mean(by_model_ssim[m])) for m in models_sorted]
 ssim_stds = [float(np.std(by_model_ssim[m])) for m in models_sorted]

 fig, ax = plt.subplots(figsize=(max(8, len(models_sorted)*1.4), 5))
 ax.bar(range(len(models_sorted)), ssim_means, yerr=ssim_stds, capsize=4,
 color="#4CAF50", edgecolor="white", alpha=0.85)
 ax.set_ylim(0, 1.05)
 ax.set_xticks(range(len(models_sorted)))
 ax.set_xticklabels(labels, rotation=20, ha="right")
 ax.set_ylabel("SSIM vs bicubic")
 ax.set_title("Calidad estructural por modelo (SSIM medio ± σ vs bicúbica)")
 ax.axhline(0.95, color="green", linestyle="--", linewidth=1, label="0.95 (referencia buena)")
 ax.legend(fontsize=9)
 ax.grid(axis="y", alpha=0.3)
 save(fig, "12b_ssim_by_model.png")

 # ── 12c: PSNR vs resolución para FSRCNN ──
 fsrcnn_rows = [r for r in rows if r["model"].startswith("FSRCNN")]
 if fsrcnn_rows:
 by_model_res = defaultdict(list)
 for r in fsrcnn_rows:
 by_model_res[r["model"]].append(r)

 scale_colors = {"FSRCNN_x2.pb": "#2196F3", "FSRCNN_x3.pb": "#4CAF50", "FSRCNN_x4.pb": "#F44336"}
 fig, ax = plt.subplots(figsize=(9, 5))
 for model in ["FSRCNN_x2.pb", "FSRCNN_x3.pb", "FSRCNN_x4.pb"]:
 pts = sorted(by_model_res.get(model, []), key=lambda x: x["pixels"])
 if not pts:
 continue
 # Promedia por resolución (distintos devices tienen mismo PSNR para mismo input)
 res_psnr = defaultdict(list)
 for p in pts:
 res_psnr[p["pixels"]].append(p["psnr"])
 xs = sorted(res_psnr)
 ys = [float(np.mean(res_psnr[x])) for x in xs]
 scale = model.split("_x")[1].replace(".pb","")
 ax.plot([x/1000 for x in xs], ys, marker="o",
 color=scale_colors[model], label=f"×{scale}", linewidth=1.8)
 ax.set_xlabel("Kpíxeles de entrada")
 ax.set_ylabel("PSNR vs bicubic (dB)")
 ax.set_title("FSRCNN: calidad vs resolución por factor de escala")
 ax.legend(title="Escala")
 ax.grid(True, alpha=0.3)
 save(fig, "12c_fsrcnn_psnr_vs_resolution.png")

 print(f"[OK] plots de calidad en {OUT_DIR}")


# ─────────────────────────────────────────────────────────────────────────────
# Tablas LaTeX para TFG
# ─────────────────────────────────────────────────────────────────────────────
def write_latex_tables(rows):
 """Genera tablas LaTeX listas para incluir en el TFG."""
 target_px = CANONICAL_W * CANONICAL_H

 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_dm = defaultdict(list)
 for r in idle_rows:
 by_dm[(r["device"], r["model"])].append(r)

 models = sorted({k[1] for k in by_dm})
 devs = [d for d in DEVICE_ORDER if any(k[0] == d for k in by_dm)]

 # ── Tabla 1: FPS a resolución canónica, todos los devices × modelos ──
 model_labels = {
 "FSRCNN_x2.pb": "FSRCNN ×2",
 "FSRCNN_x3.pb": "FSRCNN ×3",
 "FSRCNN_x4.pb": "FSRCNN ×4",
 "RealESRGAN_x4.onnx": "RealESRGAN ×4",
 "super-resolution-10.onnx": "SR-10",
 "single-image-super-resolution-1032.xml": "SISR-1032",
 }
 dev_labels = {
 "CPU_OCV": "CPU (OCV)",
 "CPU_OV": "CPU (OV)",
 "iGPU_OCL": "iGPU (OCL)",
 "iGPU_OV": "iGPU (OV)",
 "dGPU_OCL": "dGPU (OCL)",
 "dGPU_CUDA":"dGPU (CUDA)",
 }

 lines = []
 L = lines.append
 n_cols = len(models) + 1
 col_fmt = "l" + "r" * len(models)

 L(r"\begin{table}[htbp]")
 L(r" \centering")
 L(r" \caption{Throughput (FPS, p50) por dispositivo y modelo a "
 r"resolución $\approx " + f"{CANONICAL_W}\\times{CANONICAL_H}" + r"$, sin carga de sistema.}")
 L(r" \label{tab:viability_fps_idle}")
 L(r" \begin{tabular}{" + col_fmt + "}")
 L(r" \toprule")

 header = " Dispositivo & " + " & ".join(
 model_labels.get(m, m) for m in models) + r" \\"
 L(header)
 L(r" \midrule")

 for dev in devs:
 cells = [dev_labels.get(dev, dev)]
 for m in models:
 lst = _nearest_res(by_dm.get((dev, m), []), target_px)
 if lst:
 fps = max(r["fps_p50"] for r in lst)
 cells.append(f"{fps:.0f}")
 else:
 cells.append("--")
 L(" " + " & ".join(cells) + r" \\")

 L(r" \bottomrule")
 L(r" \end{tabular}")
 L(r"\end{table}")
 L("")

 # ── Tabla 2: Degradación % por device × load ──
 key2p50 = {}
 for r in rows:
 k = (r["device"], r["model"], r["input_w"], r["input_h"], r["load_tag"])
 key2p50[k] = r["p50_ms"]

 agg = defaultdict(list)
 for (dev, m, w, h, load), val in key2p50.items():
 if load == "idle":
 continue
 idle_v = key2p50.get((dev, m, w, h, "idle"))
 if idle_v and idle_v > 0:
 agg[(dev, load)].append((val - idle_v) / idle_v * 100.0)

 loads_with_data = [ld for ld in LOAD_ORDER if ld != "idle" and
 any(k[1] == ld for k in agg)]

 if loads_with_data:
 load_labels = {"cpu": "CPU stress", "igpu": "iGPU stress", "dgpu": "dGPU stress"}
 col_fmt2 = "l" + "r" * len(loads_with_data)

 L(r"\begin{table}[htbp]")
 L(r" \centering")
 L(r" \caption{Degradación media de latencia p50 (\%) respecto a idle bajo diferentes cargas del sistema.}")
 L(r" \label{tab:viability_degradation}")
 L(r" \begin{tabular}{" + col_fmt2 + "}")
 L(r" \toprule")
 hdr2 = " Dispositivo & " + " & ".join(
 load_labels.get(ld, ld) for ld in loads_with_data) + r" \\"
 L(hdr2)
 L(r" \midrule")

 devs_with_data = [d for d in DEVICE_ORDER if any(k[0] == d for k in agg)]
 for dev in devs_with_data:
 cells = [dev_labels.get(dev, dev)]
 for ld in loads_with_data:
 lst = agg.get((dev, ld), [])
 if lst:
 cells.append(f"{np.mean(lst):+.1f}\\%")
 else:
 cells.append("--")
 L(" " + " & ".join(cells) + r" \\")

 L(r" \bottomrule")
 L(r" \end{tabular}")
 L(r"\end{table}")

 out_path = Path(__file__).parent / "results" / "latex_tables.tex"
 out_path.write_text("\n".join(lines), encoding="utf-8")
 print(f"[OK] {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Resumen TFG en texto
# ─────────────────────────────────────────────────────────────────────────────
def write_text_summary(rows):
 """Genera resumen de resultados listo para referenciar en el TFG."""
 import datetime
 lines = []
 L = lines.append

 target_px = CANONICAL_W * CANONICAL_H

 idle_rows = [r for r in rows if r["load_tag"] == "idle"]
 by_dm = defaultdict(list)
 for r in idle_rows:
 by_dm[(r["device"], r["model"])].append(r)

 loads_present = sorted({r["load_tag"] for r in rows})
 devices_present = [d for d in DEVICE_ORDER if any(r["device"] == d for r in rows)]

 key2p50 = {}
 for r in rows:
 k = (r["device"], r["model"], r["input_w"], r["input_h"], r["load_tag"])
 key2p50[k] = r["p50_ms"]

 L("=" * 72)
 L("RESUMEN DE VIABILIDAD, SUPERRESOLUCIÓN EN PIPELINE DE JUEGO")
 L(f"Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
 L(f"Filas de datos: {len(rows)} | Dispositivos: {', '.join(devices_present)}")
 L(f"Estados de carga: {', '.join(loads_present)}")
 L("=" * 72)

 # --- Rendimiento idle a resolución canónica ---
 L("")
 L(f"THROUGHPUT A ~{CANONICAL_W}×{CANONICAL_H} (idle, p50)")
 L("-" * 50)
 entries = []
 for (dev, model), lst in by_dm.items():
 near = _nearest_res(lst, target_px)
 if near:
 best = max(near, key=lambda x: x["fps_p50"])
 entries.append((dev, model, best["fps_p50"], best["p50_ms"],
 best["input_w"], best["input_h"]))
 entries.sort(key=lambda e: -e[2])
 for dev, model, fps, p50, iw, ih in entries:
 viable = " 60fps" if fps >= 60 else (" 30fps" if fps >= 30 else "")
 L(f" {dev:12s} {model:38s} {fps:7.1f} FPS p50={p50:7.2f}ms [{viable}]")

 # --- Degradación por carga ---
 L("")
 L("DEGRADACIÓN MEDIA (%) BAJO CARGA vs IDLE")
 L("-" * 50)
 agg = defaultdict(list)
 for (dev, m, w, h, load), val in key2p50.items():
 if load == "idle":
 continue
 idle = key2p50.get((dev, m, w, h, "idle"))
 if idle and idle > 0:
 agg[(dev, load)].append((val - idle) / idle * 100.0)

 devs_with_data = [d for d in DEVICE_ORDER if any(k[0] == d for k in agg)]
 loads_with_data = [L2 for L2 in LOAD_ORDER if L2 != "idle" and
 any(k[1] == L2 for k in agg)]
 if devs_with_data and loads_with_data:
 header_cols = "".join(f" {ld:>8s}" for ld in loads_with_data)
 L(f" {'Dispositivo':14s}{header_cols}")
 for dev in devs_with_data:
 row_str = f" {dev:14s}"
 for ld in loads_with_data:
 lst = agg.get((dev, ld), [])
 if lst:
 row_str += f" {np.mean(lst):+7.1f}%"
 else:
 row_str += " N/A"
 L(row_str)

 # --- Viabilidad 30fps por dispositivo ---
 L("")
 L("CELDAS VIABLES A ≥30 FPS (p50 < 33.3ms)")
 L("-" * 50)
 for dev in devices_present:
 dev_rows = [r for r in idle_rows if r["device"] == dev]
 total = len(dev_rows)
 viable = sum(1 for r in dev_rows if r["fps_p50"] >= 30)
 pct = 100 * viable / total if total > 0 else 0
 L(f" {dev:14s}: {viable:3d}/{total:3d} celdas ({pct:.0f}%)")

 # --- Top resolucion por device donde es viable 60fps ---
 L("")
 L("RESOLUCIÓN MÁXIMA VIABLE A ≥60 FPS (idle, p50)")
 L("-" * 50)
 for dev in devices_present:
 viable60 = [r for r in idle_rows if r["device"] == dev and r["fps_p50"] >= 60]
 if viable60:
 best = max(viable60, key=lambda x: x["pixels"])
 L(f" {dev:14s}: {best['input_w']}×{best['input_h']} "
 f"({best['model'].replace('.pb','').replace('.onnx','').replace('.xml','')})"
 f" → {best['fps_p50']:.0f} FPS")
 else:
 L(f" {dev:14s}: ninguna celda ≥60 FPS")

 L("")
 L("=" * 72)
 L("NOTA: ONNX models (RealESRGAN_x4, super-resolution-10) solo permiten")
 L(" input 224×224 (reshape interno hardcoded). Flexible en FSRCNN (.pb).")
 L("=" * 72)

 out_path = Path(__file__).parent / "results" / "viability_summary.txt"
 out_path.write_text("\n".join(lines), encoding="utf-8")
 print(f"[OK] {out_path}")
 # Imprime también a stdout
 print("")
 for line in lines:
 print(line)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
 if not RESULTS_CSV.exists():
 print(f"[!] No encontrado: {RESULTS_CSV}", file=sys.stderr)
 sys.exit(1)

 rows = load_rows()
 if not rows:
 print("[!] CSV vacío o sin datos válidos", file=sys.stderr)
 sys.exit(1)

 print(f"Cargadas {len(rows)} filas.")
 loads_present = sorted({r["load_tag"] for r in rows})
 devices_present = sorted({r["device"] for r in rows})
 print(f"Dispositivos: {devices_present}")
 print(f"Loads: {loads_present}")

 if not HAS_MPL:
 print("[!] matplotlib no disponible, saltando plots", file=sys.stderr)
 else:
 print(f"\nGenerando plots en {OUT_DIR} ...")
 plot_latency_vs_resolution(rows)
 plot_heatmap_interference(rows)
 plot_fps_bar_idle(rows)
 plot_fps_grouped_load(rows)
 plot_fsrcnn_scale_comparison(rows)
 plot_heatmap_fps_idle(rows)
 plot_boxplot_by_device(rows)
 plot_cdf(rows)
 plot_degradation_bars(rows)
 plot_scatter_pixels_fps(rows)
 plot_best_device_per_model(rows)

 print("\nGenerando CSVs ...")
 write_ranking(rows)
 write_full_stats(rows)
 write_text_summary(rows)
 write_latex_tables(rows)
 plot_quality_metrics()
 print("\nListo.")


if __name__ == "__main__":
 main()
