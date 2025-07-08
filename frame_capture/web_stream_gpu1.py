import posix_ipc
import mmap
import numpy as np
import torch
import torch.nn.functional as F
import cv2
from flask import Flask, Response

SHM_NAME = "/framebuffer_shm"
FRAME_WIDTH, FRAME_HEIGHT = 640, 480
FRAME_CHANNELS = 4
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT * FRAME_CHANNELS

# Cargar la memoria compartida
shm = posix_ipc.SharedMemory(SHM_NAME)
mapfile = mmap.mmap(shm.fd, FRAME_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
shm.close_fd()

# Inicializar modelo de superresolución (bilinear upscaling simulado)
def upscale(frame_tensor):
    return F.interpolate(frame_tensor.unsqueeze(0), scale_factor=2, mode='bilinear', align_corners=False).squeeze(0)

# Flask
app = Flask(__name__)

def gen():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando dispositivo: {device}")

    while True:
        mapfile.seek(0)
        frame_bytes = mapfile.read(FRAME_SIZE)
        frame_np = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((FRAME_HEIGHT, FRAME_WIDTH, FRAME_CHANNELS))
        frame_np = frame_np[:, :, :3]  # RGB

        # Convertir a tensor y escalar
        frame_tensor = torch.from_numpy(frame_np).float().permute(2, 0, 1).to(device) / 255.0
        upscaled_tensor = upscale(frame_tensor)

        # Convertir a imagen OpenCV
        upscaled_np = (upscaled_tensor.clamp(0, 1).cpu().permute(1, 2, 0).numpy() * 255).astype(np.uint8)
        _, jpeg = cv2.imencode('.jpg', upscaled_np[:, :, ::-1])  # RGB to BGR

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
