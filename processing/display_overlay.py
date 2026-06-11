"""Ventana única: overlay fullscreen con la salida reescalada por IA.

Modo "opción B" del proyecto: el juego corre debajo (ventana pequeña, render
en dGPU) y solo se ve esta ventana fullscreen con el frame reescalado por
FSRCNN/OpenVINO en la iGPU. El foco de teclado se devuelve a la ventana del
juego nada más crear el overlay, y durante el juego el puntero queda capturado
por el juego (mouse-look), de modo que el input va al juego aunque mires el
overlay. No se modifica el contexto OpenGL del juego ni se reenvía input.

Variables de entorno:
  FSRCNN_SCALE      = 4 (def) | 2
  GAME_WINDOW_NAME  = "Minecraft" (def)   nombre para devolver el foco con xdotool
  DISPLAY           = :1 (def)
"""
import os
import struct
import subprocess
import sys
import time

import cv2
import numpy as np
import openvino as ov

os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("DISPLAY", ":1")
import pygame  # noqa: E402  (tras fijar el backend SDL)

SHM_NAME = "/dev/shm/framebuffer_shared"
HEADER_FMT = "IIII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_DIM = 8192

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = int(os.environ.get("FSRCNN_SCALE", "4"))
MODEL_XML = os.path.join(REPO_DIR, "models", f"fsrcnn_x{SCALE}_ov.xml")
IN_W, IN_H = (480, 270) if SCALE == 4 else (960, 540)
GAME_WINDOW_NAME = os.environ.get("GAME_WINDOW_NAME", "Minecraft")

core = ov.Core()
device = "GPU" if "GPU" in core.available_devices else "CPU"
compiled = core.compile_model(core.read_model(MODEL_XML), device,
                              {"CACHE_DIR": "/tmp/openvino_cache"})
infer = compiled.create_infer_request()
print(f"[INFO] {device}, modelo FSRCNN x{SCALE} ({IN_W}x{IN_H})")


def read_frame(last_seq):
    try:
        fd = os.open(SHM_NAME, os.O_RDONLY)
        try:
            h = os.read(fd, HEADER_SIZE)
            if len(h) < HEADER_SIZE:
                return None, last_seq
            w, ht, seq, ready = struct.unpack(HEADER_FMT, h)
            if not ready or seq == last_seq or not (0 < w <= MAX_DIM and 0 < ht <= MAX_DIM):
                return None, last_seq
            buf = os.read(fd, w * ht * 4)
            if len(buf) < w * ht * 4:
                return None, last_seq
        finally:
            os.close(fd)
        frame = np.frombuffer(buf, np.uint8).reshape((ht, w, 4))
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR), seq
    except FileNotFoundError:
        return None, last_seq


def upscale_rgb(frame_bgr):
    """Devuelve la imagen reescalada en RGB (lista para pygame)."""
    small = cv2.resize(frame_bgr, (IN_W, IN_H))
    ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
    infer.infer({0: y})
    y_up = (infer.get_output_tensor().data[0, 0] * 255).clip(0, 255).astype(np.uint8)
    oh, ow = y_up.shape
    cr = cv2.resize(ycrcb[:, :, 1], (ow, oh))
    cb = cv2.resize(ycrcb[:, :, 2], (ow, oh))
    bgr = cv2.cvtColor(cv2.merge([y_up, cr, cb]), cv2.COLOR_YCrCb2BGR)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def return_focus_to_game():
    """Devuelve el foco de teclado a la ventana del juego (queda debajo)."""
    try:
        subprocess.run(["xdotool", "search", "--name", GAME_WINDOW_NAME,
                        "windowactivate", "--sync"],
                       env={**os.environ, "DISPLAY": os.environ["DISPLAY"]},
                       timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[WARN] no se pudo devolver el foco al juego: {e}")


def main():
    pygame.init()
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    screen = pygame.display.set_mode((sw, sh), pygame.NOFRAME)
    pygame.display.set_caption("AI Upscaling Overlay")
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(False)
    # Que SDL no robe el puntero; el foco vuelve al juego:
    time.sleep(0.3)
    return_focus_to_game()

    print(f"[INFO] Overlay {sw}x{sh}. El input va al juego (debajo). "
          f"Ctrl+C en la terminal para salir.")
    last_seq, n, acc, missing = 0, 0, 0.0, 0
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); return

        frame, seq = read_frame(last_seq)
        if frame is None:
            missing += 1
            if missing > 600:  # ~ varios segundos sin frames → juego cerrado
                print("[INFO] Sin frames; saliendo.")
                break
            clock.tick(120)
            continue
        missing = 0
        last_seq = seq

        t0 = time.time()
        rgb = upscale_rgb(frame)
        acc += (time.time() - t0) * 1000
        n += 1
        if n % 60 == 0:
            avg = acc / 60
            print(f"[INFO] {n} frames: {avg:.1f} ms (~{1000/avg:.0f} FPS)")
            acc = 0.0

        oh, ow = rgb.shape[:2]
        surf = pygame.image.frombuffer(rgb.tobytes(), (ow, oh), "RGB")
        if (ow, oh) != (sw, sh):
            surf = pygame.transform.scale(surf, (sw, sh))
        screen.blit(surf, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
