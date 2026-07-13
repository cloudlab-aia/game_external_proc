import cv2
import numpy as np
import time
import os
import onnxruntime as ort

# ===========================
# CONFIGURACIÓN
# ===========================
MODELS_DIR = "/home/ogg/Desktop/AIA/game_external_proc/models/"
MODEL_FILES = [
    "FSRCNN_x2.pb",
    "FSRCNN_x3.pb",
    "FSRCNN_x4.pb",
    "RealESRGAN_x4.onnx"
]

INPUT_RESOLUTIONS = [
    (128, 72),
    (640, 360),
    (1280, 720),
    (1920, 1080),
    (2560, 1440)
]

OUTPUT_SIZE = (3840, 2160)  # Salida 4K
DEVICE = "igpu"  # CPU o iGPU

# ===========================
# CARGA DE MODELOS
# ===========================
def load_fsrcnn(model_path):
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model_path)
    scale = int(model_path.split("_x")[-1].split(".")[0])
    sr.setModel("fsrcnn", scale)
    if DEVICE == "igpu":
        sr.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
    else:
        sr.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return sr

def load_realesrgan(model_path):
    providers = ['CPUExecutionProvider']
    if DEVICE == "igpu":
        providers = ['OpenVINOExecutionProvider', 'CPUExecutionProvider']
    sess = ort.InferenceSession(model_path, providers=providers)
    return sess

# ===========================
# CAPTURA DE VENTANA (glxgears)
# ===========================
def capture_window():
    # Captura la pantalla principal (0) o adaptarlo a otra fuente
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la captura de video")
    return cap

# ===========================
# BUCLE PRINCIPAL
# ===========================
def run_experiment():
    # Cargar modelos
    loaded_models = {}
    for mf in MODEL_FILES:
        path = os.path.join(MODELS_DIR, mf)
        if mf.startswith("FSRCNN"):
            loaded_models[mf] = load_fsrcnn(path)
        else:
            loaded_models[mf] = load_realesrgan(path)

    cap = capture_window()

    for w_in, h_in in INPUT_RESOLUTIONS:
        ret, frame = cap.read()
