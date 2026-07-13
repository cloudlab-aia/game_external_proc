"""Mide los FPS de render del juego leyendo el contador de frames del buzón.

El wrapper incrementa `seq` en cada frame que captura (uno por glXSwapBuffers),
así que la tasa de `seq` por segundo = los FPS reales que la dGPU está
produciendo, a cualquier resolución. No necesita la IA: mide solo el render.

Sirve para el experimento de shaders: medir los FPS del juego a resolución
nativa (1080p) vs a baja resolución, con el mismo shader pack y escena.

Uso (con el juego renderizando y capturándose):
    python3 benchmarks/render_fps.py --seconds 15
"""
import argparse
import struct
import time

SHM = "/dev/shm/framebuffer_shared"
HDR = "IIII"
HDR_SZ = struct.calcsize(HDR)


def read_header():
    try:
        with open(SHM, "rb") as f:
            d = f.read(HDR_SZ)
        if len(d) < HDR_SZ:
            return None
        return struct.unpack(HDR, d)  # w, h, seq, ready
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=15.0, help="ventana de medida")
    ap.add_argument("--interval", type=float, default=1.0, help="cada cuánto reporta")
    args = ap.parse_args()

    h = read_header()
    if h is None:
        raise SystemExit(f"No hay captura en {SHM}. ¿Está el juego renderizándose con el wrapper?")
    w, ht = h[0], h[1]
    print(f"[INFO] Resolución de render capturada: {w}x{ht}")
    print(f"[INFO] Midiendo FPS durante {args.seconds:.0f}s...\n")

    t_start = time.monotonic()
    seq_start = read_header()[2]
    last_t, last_seq = t_start, seq_start
    samples = []
    while time.monotonic() - t_start < args.seconds:
        time.sleep(args.interval)
        hdr = read_header()
        if hdr is None:
            continue
        now = time.monotonic()
        fps = (hdr[2] - last_seq) / (now - last_t)
        samples.append(fps)
        print(f"  {now - t_start:5.1f}s   {fps:7.1f} FPS   ({hdr[0]}x{hdr[1]})")
        last_t, last_seq = now, hdr[2]

    end = read_header()
    total_t = time.monotonic() - t_start
    avg = (end[2] - seq_start) / total_t
    print(f"\n=== Render {w}x{ht}: {avg:.1f} FPS de media "
          f"({end[2]-seq_start} frames en {total_t:.1f}s) ===")
    if samples:
        print(f"    min {min(samples):.1f} / max {max(samples):.1f} FPS")


if __name__ == "__main__":
    main()
