import os
import cv2
import time
import numpy as np
from flask import Flask, Response

# Configuración
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/framebuffer_shared"
MODEL_PATH = "/workspace/models/super-resolution-10.onnx"

# Inicializa Flask
app = Flask(__name__)

# Carga modelo ONNX
print("[INFO] Cargando modelo ONNX:", MODEL_PATH)
net = cv2.dnn.readNetFromONNX(MODEL_PATH)

# Usa la iGPU (OpenCL) si está disponible
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)

def upscale_frame(frame_bgr):
    """Aplica superresolución x2 usando el modelo ONNX."""
    img_ycc = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(img_ycc)

    # El modelo solo trabaja con el canal Y (luminancia)
    blob = cv2.dnn.blobFromImage(y.astype(np.float32) / 255.0)
    net.setInput(blob)
    out = net.forward()[0, 0]
    out_y = (out * 255.0).clip(0, 255).astype(np.uint8)

    # Reconstruye la imagen final
    h, w = out_y.shape
    cr_up = cv2.resize(cr, (w, h), interpolation=cv2.INTER_CUBIC)
    cb_up = cv2.resize(cb, (w, h), interpolation=cv2.INTER_CUBIC)
    img_ycc_up = cv2.merge([out_y, cr_up, cb_up])
    return cv2.cvtColor(img_ycc_up, cv2.COLOR_YCrCb2BGR)

def get_shared_frame():
    """Lee un frame desde la memoria compartida."""
    try:
        fd = os.open(SHM_NAME, os.O_RDONLY)
        buf = os.read(fd, FRAME_SIZE)
        os.close(fd)
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))
        frame_bgr = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR)
        return frame_bgr
    except Exception as e:
        print("[WARN] Error al leer frame compartido:", e)
        return None

def generate():
    """Generador de frames para Flask."""
    while True:
        frame = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            frame_up = upscale_frame(frame)
            _, jpeg = cv2.imencode('.jpg', frame_up)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        except Exception as e:
            print("[ERROR] Error durante procesamiento:", e)

@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print("[INFO] Iniciando servidor Flask en http://localhost:5000/video_feed")
    app.run(host="0.0.0.0", port=5000, threaded=True)
