#!/bin/bash
# Arquitectura final, en un comando:
#   launcher VISIBLE en la sesión al darle a Jugar, el juego va
#   a la pantalla virtual oculta (:2) con PRIME + captura sin presentar
#   (CAPTURE_SKIP_PRESENT) -> la iGPU reconstruye con FSRCNN
#
# Uso:  pipeline/run_arquitectura_final.sh
# Ajustes por entorno: GAME_W/GAME_H (def. 640x360), FSRCNN_SCALE (def. 3)
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
REPO="$PWD"
PY="$REPO/venv/bin/python3"; [ -x "$PY" ] || PY=python3
LAUNCHER="${LAUNCHER:-$HOME/Desktop/minecraft-launcher/minecraft-launcher}"
SESION="${DISPLAY:-:1}"          # tu pantalla real
VIRT=":2"                        # la pantalla oculta
GAME_W="${GAME_W:-640}"; GAME_H="${GAME_H:-360}"
SCALE="${FSRCNN_SCALE:-3}"
SHM=/dev/shm/framebuffer_shared

cleanup() {
    echo; echo ">>> Cerrando todo..."
    pkill -f display_overlay_forward 2>/dev/null
    pkill -f "net.minecraft" 2>/dev/null; pkill java 2>/dev/null
    pkill -f minecraft-launcher 2>/dev/null
    pkill -f "Xvfb $VIRT" 2>/dev/null
    rm -f "$SHM"
}
trap cleanup EXIT INT TERM

echo "[1/5] Limpieza previa..."
pkill -f display_overlay_forward 2>/dev/null; pkill -f upscale_consumer 2>/dev/null
pkill -f "Xvfb $VIRT" 2>/dev/null; pkill -f "net.minecraft" 2>/dev/null
rm -f "$SHM" /tmp/.X2-lock /tmp/.X11-unix/X2
rm -f "$HOME/.minecraft/webcache2/"Singleton* 2>/dev/null   # lock rancio de Electron
sleep 1

echo "[2/5] Pantalla virtual oculta ($VIRT, ${VIRT_RES:-1920x1080x24})..."
Xvfb "$VIRT" -screen 0 "${VIRT_RES:-1920x1080x24}" &>/tmp/xvfb_final.log &
sleep 2
[ -e /tmp/.X11-unix/X2 ] || { echo "ERROR: Xvfb no arrancó"; exit 1; }

echo "[3/5] Launcher visible en $SESION (inicia sesión y dale a JUGAR)..."
env DISPLAY="$SESION" \
    LD_PRELOAD="$REPO/capture/game_launch_interposer.so" \
    GAME_VIRT_DISPLAY="$VIRT" \
    GAME_VGL_PRELOAD="$REPO/capture/wrapper_swapbuffers_shm.so" \
    GAME_EXTRA_ENV="__NV_PRIME_RENDER_OFFLOAD=1;__GLX_VENDOR_LIBRARY_NAME=nvidia;CAPTURE_SKIP_PRESENT=1;FRAME_CAPTURE_EXE=java" \
    "$LAUNCHER" &>/tmp/launcher_final.log &

echo -n "[4/5] Esperando a que el juego produzca frames"
while [ ! -e "$SHM" ]; do echo -n "."; sleep 2; done
echo " capturando!"

# comprobar que el interposer lo mandó bien a :2 con skip-present
JP=$(pgrep -f "net.minecraft.client.main.Main" | head -1)
if [ -n "$JP" ]; then
    DISP=$(tr '\0' '\n' </proc/$JP/environ 2>/dev/null | grep '^DISPLAY=' | cut -d= -f2)
    SKIP=$(tr '\0' '\n' </proc/$JP/environ 2>/dev/null | grep -c '^CAPTURE_SKIP_PRESENT=1')
    if [ "$DISP" != "$VIRT" ] || [ "$SKIP" != "1" ]; then
        echo "AVISO: el interposer no enganchó bien (DISPLAY=$DISP, skip=$SKIP)."
        echo "       Cierra el juego desde el launcher y dale a JUGAR otra vez."
    else
        echo "      Juego en $VIRT con skip-present (render GPU-bound, oculto)"
    fi
fi

# encoger el render del juego (modo según escala: x3 -> 640x360)
sleep 2
GW=$(DISPLAY=$VIRT xdotool search --name "Minecraft\*" 2>/dev/null | tail -1)
[ -z "$GW" ] && GW=$(DISPLAY=$VIRT xdotool search --name "1\.2" 2>/dev/null | tail -1)
[ -n "$GW" ] && DISPLAY=$VIRT xdotool windowsize "$GW" "$GAME_W" "$GAME_H" 2>/dev/null \
    && echo "      Render del juego a ${GAME_W}x${GAME_H}"

INFER_DEVICE="${INFER_DEVICE:-iGPU}"
echo "[5/5] Overlay (IA x$SCALE en $INFER_DEVICE -> 1080p). F12 o Ctrl+C aquí para salir."
if [ "$INFER_DEVICE" = "dGPU" ]; then
    QT_QPA_PLATFORM=xcb DISPLAY="$SESION" TARGET_DISPLAY="$VIRT" \
        FSRCNN_SCALE="$SCALE" INFER_DEVICE="$INFER_DEVICE" "$PY" "$REPO/processing/display_overlay_forward.py"
else
    QT_QPA_PLATFORM=xcb CUDA_VISIBLE_DEVICES="" DISPLAY="$SESION" TARGET_DISPLAY="$VIRT" \
        FSRCNN_SCALE="$SCALE" INFER_DEVICE="$INFER_DEVICE" "$PY" "$REPO/processing/display_overlay_forward.py"
fi

# Con KEEP_GAME=1, al cerrar el overlay el juego sigue vivo en la pantalla
# virtual (para lanzar scripts de medicion sin el consumidor). Terminar con:
# pkill java; pkill -f "Xvfb :2"
if [ "${KEEP_GAME:-0}" = "1" ]; then
    trap - EXIT INT TERM
    echo ""
    echo ">>> KEEP_GAME=1: overlay cerrado, el juego sigue capturando en $VIRT."
    echo ">>> Termina con: pkill java; pkill -f 'Xvfb $VIRT'"
    exit 0
fi
