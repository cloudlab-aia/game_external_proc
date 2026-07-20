#!/bin/bash
# Captura un frame del juego a alta resolucion para las comparativas de
# calidad: sube la ventana a la resolucion pedida, espera a que estabilice,
# vuelca el frame del shm a PNG y devuelve la ventana a su tamano original.
#
# REQUISITOS: juego en vivo capturandose en la pantalla virtual (el overlay
# puede estar abierto; el frame se lee del shm igualmente).
#
# Uso: experiments/grab_frame.sh <salida.png> [WxH_captura] [WxH_vuelta] [display]
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="venv/bin/python3"
SHM="/dev/shm/framebuffer_shared"
OUT="${1:?Uso: grab_frame.sh salida.png [WxH] [WxH_vuelta] [display]}"
RES="${2:-3840x2160}"; BACK="${3:-640x360}"; DISP="${4:-:2}"

[ -f "$SHM" ] || { echo "No hay captura activa"; exit 1; }
GW=$(DISPLAY=$DISP xdotool search --name Minecraft 2>/dev/null | tail -1)
[ -z "$GW" ] && { echo "Sin ventana de juego en $DISP"; exit 1; }

W=${RES%x*}; H=${RES#*x}
DISPLAY=$DISP xdotool windowsize "$GW" "$W" "$H"
$PY - "$OUT" "$W" "$H" << 'EOF'
import struct, sys, time
import numpy as np
import cv2
out, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
shm = "/dev/shm/framebuffer_shared"
for _ in range(100):
    w, h, s, r = struct.unpack("IIII", open(shm, "rb").read(16))
    if abs(w - W) <= 6 and abs(h - H) <= 6:
        break
    time.sleep(0.1)
else:
    sys.exit(f"la resolucion no llego a {W}x{H} (efectiva {w}x{h})")
time.sleep(2)
with open(shm, "rb") as f:
    w, h, s, r = struct.unpack("IIII", f.read(16))
    frame = np.frombuffer(f.read(w * h * 4), dtype=np.uint8).reshape((h, w, 4))
cv2.imwrite(out, cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR))
print(f"guardado {out} ({w}x{h}, seq {s})")
EOF
BW=${BACK%x*}; BH=${BACK#*x}
DISPLAY=$DISP xdotool windowsize "$GW" "$BW" "$BH"
echo "ventana devuelta a $BACK"
