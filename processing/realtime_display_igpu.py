import os
import cv2
import time
import numpy as np

# Configuración
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/framebuffer_shared"
MODEL_PATH = "/workspace/models/super-resolution-10.onnx"

print("[INFO] Cargando modelo ONNX:", MODEL_PATH)
net = cv2.dnn.readNetFromONNX(MODEL_PATH)

# Fuerza uso de iGPU via OpenCL
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)

# Verifica qué dispositivo OpenCL se está usando
if cv2.ocl.haveOpenCL():
    cv2.ocl.setUseOpenCL(True)
    ctx = cv2.ocl.Context()
    if ctx.create(cv2.ocl.Device.TYPE_GPU):
        print(f"[INFO] Dispositivo OpenCL seleccionado: {ctx.device(0).name()}")
    else:
        print("[WARN] No se pudo crear contexto OpenCL con GPU")
else:
    print("[WARN] OpenCL no está disponible")

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

def main_loop():
    """Bucle principal: lee, procesa y muestra frames."""
    print("[INFO] Iniciando bucle de visualización en tiempo real")
    while True:
        frame = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        start = time.time()
        try:
            frame_up = upscale_frame(frame)
        except Exception as e:
            print("[ERROR] Fallo en upscaling:", e)
            continue
        end = time.time()

        # Muestra el frame con FPS aproximado
        fps = 1 / (end - start)
        cv2.putText(frame_up, f"FPS IA: {fps:.2f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Frame Upscaled (iGPU)", frame_up)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("[INFO] Cerrando ventana")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main_loop()
