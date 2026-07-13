#!/usr/bin/env python3
import os
import cv2
import time
import numpy as np
from flask import Flask, Response
from threading import Thread
import posix_ipc
import mmap

# --- CONFIGURACIÓN DE MEMORIA COMPARTIDA ---
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/framebuffer_shared"

# Captura desde memoria compartida
def read_shared_frame():
    # Espera a que la memoria compartida exista
    while True:
        try:
            shm = posix_ipc.SharedMemory(SHM_NAME)
            break
        except posix_ipc.ExistentialError:
            print(f"Esperando a que la memoria compartida '{SHM_NAME}' se cree...")
            time.sleep(1)

    mapfile = mmap.mmap(shm.fd, FRAME_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
    shm.close_fd()
    
    print("Lector conectado a la memoria compartida.")

    while True:
        mapfile.seek(0)
        frame_bytes = mapfile.read(FRAME_SIZE)
        frame_np = np.frombuffer(frame_bytes, dtype=np.uint8).copy()
        # El wrapper guarda en RGBA, lo convertimos a BGR para OpenCV
        frame_rgba = frame_np.reshape((HEIGHT, WIDTH, 4))
        frame_bgr = cv2.cvtColor(frame_rgba, cv2.COLOR_RGBA2BGR)
        yield frame_bgr

# Upscaling con OpenCV (sin modelos)
def upscale_frame(frame):
    # Escalado por 2 usando interpolación bicúbica
    return cv2.resize(frame, (frame.shape[1] * 2, frame.shape[0] * 2), interpolation=cv2.INTER_CUBIC)

# Servidor Flask para streaming
app = Flask(__name__)
frame_generator = read_shared_frame()

def generate_stream():
    for frame in frame_generator:
        upscaled = upscale_frame(frame)
        ret, jpeg = cv2.imencode('.jpg', upscaled)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(1/30)

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    print("Servidor Flask iniciado en http://localhost:5000/video_feed")