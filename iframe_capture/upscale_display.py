import os
import cv2
import time
import numpy as np

# Configuración
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/dev/shm/framebuffer_shared"
MODEL_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models/super-resolution-10.onnx"

# === ENV VARS: Forzar Intel iGPU específicamente ===
os.environ["OPENCV_DNN_OPENCL_ALLOW_ALL_DEVICES"] = "1"
# Fuerza Intel específicamente usando índice de plataforma (Intel=1, NVIDIA=0)
os.environ["OPENCV_OCL_DEVICE"] = "1:GPU:0"  # Plataforma 1 (Intel), GPU 0
# Alternativas para forzar Intel
os.environ["OPENCL_VENDOR"] = "Intel"  # Prioriza Intel como vendor
os.environ["INTEL_OPENCL_ICD"] = "1"  # Habilita Intel OpenCL ICD
# Deshabilita NVIDIA completamente
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Oculta NVIDIA CUDA
os.environ["__NV_PRIME_RENDER_OFFLOAD"] = "0"  # Desactiva NVIDIA Prime
os.environ["__GLX_VENDOR_LIBRARY_NAME"] = "intel"  # Fuerza Intel para GLX
os.environ["OPENCV_LOG_LEVEL"] = "INFO"  # Habilitar logs para debug

# === Cargar modelo ONNX ===
print("[INFO] Cargando modelo ONNX:", MODEL_PATH)
net = cv2.dnn.readNetFromONNX(MODEL_PATH)

# === Función para configurar Intel iGPU ===
def configurar_intel_igpu():
    """Configura OpenCV para usar Intel iGPU mediante OpenCL"""
    if not cv2.ocl.haveOpenCL():
        print("[ERROR] OpenCL no está disponible en OpenCV")
        return False

    # Habilitar OpenCL
    cv2.ocl.setUseOpenCL(True)
    
    try:
        # Configurar DNN para usar OpenCL (Intel iGPU)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
        
        # Verificar que OpenCL esté activo
        if cv2.ocl.useOpenCL():
            print("[INFO] OpenCL habilitado exitosamente")
            print("[INFO] DNN configurado para usar OpenCL")
            print("[INFO] Debería estar usando Intel iGPU (plataforma 1)")
            return True
        else:
            print("[WARN] OpenCL no se pudo activar")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error configurando OpenCL: {e}")
        return False

def verificar_opencl_status():
    """Verifica el estado de OpenCL"""
    try:
        if cv2.ocl.haveOpenCL():
            if cv2.ocl.useOpenCL():
                print("[INFO] OpenCL disponible y activo")
                return True
            else:
                print("[WARN] OpenCL disponible pero no activo")
                return False
        else:
            print("[ERROR] OpenCL no disponible")
            return False
    except Exception as e:
        print(f"[ERROR] Error verificando OpenCL: {e}")
        return False

# === Inicializar Intel iGPU ===
print("[INFO] Inicializando Intel iGPU...")
igpu_ok = configurar_intel_igpu()

# Verificar estado de OpenCL
verificar_opencl_status()

# Si no hay iGPU, usar CPU como fallback
if not igpu_ok:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    print("[WARN] Cayendo en CPU como fallback")
else:
    print("[INFO] Intel iGPU configurada exitosamente")

# === Superresolución ===
def upscale_frame(frame_bgr):
    h_orig, w_orig = frame_bgr.shape[:2]
    frame_small = cv2.resize(frame_bgr, (224, 224))
    img_ycc = cv2.cvtColor(frame_small, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(img_ycc)

    blob = cv2.dnn.blobFromImage(y.astype(np.float32) / 255.0, scalefactor=1.0, size=(224, 224))
    net.setInput(blob)
    out = net.forward()[0, 0]
    out_y = (out * 255.0).clip(0, 255).astype(np.uint8)

    cr_up = cv2.resize(cr, out_y.shape[::-1], interpolation=cv2.INTER_CUBIC)
    cb_up = cv2.resize(cb, out_y.shape[::-1], interpolation=cv2.INTER_CUBIC)

    img_ycc_up = cv2.merge([out_y, cr_up, cb_up])
    img_bgr_up = cv2.cvtColor(img_ycc_up, cv2.COLOR_YCrCb2BGR)
    final_result = cv2.resize(img_bgr_up, (w_orig * 2, h_orig * 2), interpolation=cv2.INTER_CUBIC)

    return final_result

# === Leer de memoria compartida ===
def get_shared_frame():
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

# === Main loop ===
if __name__ == "__main__":
    print("[INFO] Mostrando ventana OpenCV con IA aplicada. Pulsa 'q' para salir.")
    while True:
        frame = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            start = time.time()
            frame_up = upscale_frame(frame)
            latency = (time.time() - start) * 1000
            print(f"[INFO] Latencia IA: {latency:.2f} ms")
            cv2.imshow("Frame con IA (iGPU Intel)", frame_up)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("[ERROR] Error en procesamiento:", e)
            time.sleep(0.1)

    cv2.destroyAllWindows()
