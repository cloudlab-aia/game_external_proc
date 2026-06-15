"""Overlay con reenvío de input — modo pantalla virtual.

Muestra en una ventana real (display :1) los frames reescalados por IA que
produce el juego corriendo en una PANTALLA VIRTUAL (Xvfb, p. ej. :2), y
reenvía el teclado y el ratón capturados en :1 hacia el juego en :2 mediante
XTEST. Así el juego corre oculto (render dGPU vía VirtualGL) y tú lo controlas
y lo ves, reescalado, en tiempo real.

A diferencia de display_overlay.py (que es click-through y no roba foco, para
cuando el juego está en el MISMO display), aquí la ventana SÍ toma el foco y
captura el input para reenviarlo al display virtual.

Variables de entorno:
  TARGET_DISPLAY = :2 (def)   display virtual donde corre el juego
  FSRCNN_SCALE   = 4 (def)
  DISPLAY        = :1 (def)   donde se ve el overlay y se captura el input
"""
import os
import struct
import time

import cv2
import numpy as np
import openvino as ov

os.environ.setdefault("SDL_VIDEODRIVER", "x11")
os.environ.setdefault("DISPLAY", ":1")
import pygame  # noqa: E402

from Xlib import X, display as xdisplay, XK  # noqa: E402
from Xlib.ext import xtest  # noqa: E402

SHM_NAME = "/dev/shm/framebuffer_shared"
HEADER_FMT = "IIII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_DIM = 8192

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = int(os.environ.get("FSRCNN_SCALE", "4"))
MODEL_XML = os.path.join(REPO_DIR, "models", "openvino_ir", f"FSRCNN_x{SCALE}.xml")
IN_W, IN_H = {4: (480, 270), 3: (640, 360), 2: (960, 540)}[SCALE]
TARGET_DISPLAY = os.environ.get("TARGET_DISPLAY", ":2")

# --- Mapa de teclas pygame -> nombre de keysym X (teclas no imprimibles) ---
SPECIAL_KEYS = {
    pygame.K_SPACE: "space", pygame.K_RETURN: "Return", pygame.K_ESCAPE: "Escape",
    pygame.K_TAB: "Tab", pygame.K_BACKSPACE: "BackSpace",
    pygame.K_LSHIFT: "Shift_L", pygame.K_RSHIFT: "Shift_R",
    pygame.K_LCTRL: "Control_L", pygame.K_RCTRL: "Control_R",
    pygame.K_LALT: "Alt_L", pygame.K_RALT: "Alt_R",
    pygame.K_UP: "Up", pygame.K_DOWN: "Down", pygame.K_LEFT: "Left", pygame.K_RIGHT: "Right",
    pygame.K_F1: "F1", pygame.K_F2: "F2", pygame.K_F3: "F3", pygame.K_F5: "F5",
    pygame.K_F11: "F11", pygame.K_LSUPER: "Super_L",
}


class InputForwarder:
    """Reinyecta teclado/ratón en el display virtual vía XTEST."""

    def __init__(self, target_display):
        self.d = xdisplay.Display(target_display)
        self._cache = {}

    def _keycode(self, keysym_name):
        if keysym_name not in self._cache:
            ks = XK.string_to_keysym(keysym_name)
            self._cache[keysym_name] = self.d.keysym_to_keycode(ks) if ks else 0
        return self._cache[keysym_name]

    def key(self, pygame_key, unicode_char, press):
        name = SPECIAL_KEYS.get(pygame_key)
        if name is None and unicode_char and unicode_char.isprintable() and unicode_char != " ":
            name = unicode_char
        if not name:
            return
        kc = self._keycode(name)
        if kc:
            xtest.fake_input(self.d, X.KeyPress if press else X.KeyRelease, kc)
            self.d.sync()

    def motion(self, dx, dy):
        if dx or dy:
            xtest.fake_input(self.d, X.MotionNotify, detail=True, x=int(dx), y=int(dy))
            self.d.sync()

    def button(self, btn, press):
        xtest.fake_input(self.d, X.ButtonPress if press else X.ButtonRelease, btn)
        self.d.sync()


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
        return cv2.cvtColor(np.frombuffer(buf, np.uint8).reshape((ht, w, 4)), cv2.COLOR_RGBA2BGR), seq
    except FileNotFoundError:
        return None, last_seq


def main():
    core = ov.Core()
    dev = "GPU" if "GPU" in core.available_devices else "CPU"
    m = core.read_model(MODEL_XML)
    m.reshape([1, IN_H, IN_W, 1])
    compiled = core.compile_model(m, dev, {"CACHE_DIR": "/tmp/openvino_cache"})
    infer = compiled.create_infer_request()
    print(f"[INFO] {dev}, FSRCNN x{SCALE}; reenvío de input a {TARGET_DISPLAY}")

    fwd = InputForwarder(TARGET_DISPLAY)

    pygame.init()
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    screen = pygame.display.set_mode((sw, sh), pygame.NOFRAME)
    pygame.display.set_caption("Hybrid (virtual screen)")
    pygame.event.set_grab(True)          # capturar todo el input
    pygame.mouse.set_visible(False)
    pygame.mouse.get_rel()               # descartar primer delta
    print("[INFO] Input capturado y reenviado. ESC físico (F12) para salir.")

    last_seq = 0
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F12:   # salida de emergencia (no se reenvía)
                    running = False
                else:
                    fwd.key(ev.key, ev.unicode, True)
            elif ev.type == pygame.KEYUP:
                fwd.key(ev.key, ev.unicode, False)
            elif ev.type == pygame.MOUSEMOTION:
                dx, dy = ev.rel
                fwd.motion(dx, dy)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                fwd.button(ev.button, True)
            elif ev.type == pygame.MOUSEBUTTONUP:
                fwd.button(ev.button, False)

        frame, seq = read_frame(last_seq)
        if frame is None:
            pygame.time.wait(2)
            continue
        last_seq = seq
        ycrcb = cv2.cvtColor(cv2.resize(frame, (IN_W, IN_H)), cv2.COLOR_BGR2YCrCb)
        y = ycrcb[:, :, 0].astype(np.float32)[None, :, :, None] / 255.0
        infer.infer({0: y})
        y_up = (np.squeeze(infer.get_output_tensor().data) * 255).clip(0, 255).astype(np.uint8)
        oh, ow = y_up.shape
        cr = cv2.resize(ycrcb[:, :, 1], (ow, oh)); cb = cv2.resize(ycrcb[:, :, 2], (ow, oh))
        rgb = cv2.cvtColor(cv2.cvtColor(cv2.merge([y_up, cr, cb]), cv2.COLOR_YCrCb2BGR), cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(rgb.tobytes(), (ow, oh), "RGB")
        if (ow, oh) != (sw, sh):
            surf = pygame.transform.scale(surf, (sw, sh))
        screen.blit(surf, (0, 0))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
