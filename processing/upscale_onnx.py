import cv2
import numpy as np
import onnxruntime as ort

# ===== CONFIGURACIÓN =====
MODEL_PATH = "/home/ogg/Desktop/AIA/game_external_proc/models/modelo.onnx"
INPUT_SOURCE = "frame.jpg"  # Puede ser 0 para webcam o ruta a imagen
# =========================

# Cargar modelo ONNX
session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
input_shape = session.get_inputs()[0].shape  # Ej: [1, 3, 224, 224] o [1, 1, 224, 224]

print(f"[INFO] Modelo cargado: {MODEL_PATH}")
print(f"[INFO] Nombre de entrada: {input_name}")
print(f"[INFO] Forma esperada: {input_shape}")

# Detectar canales y dimensiones requeridas
batch, channels, height, width = input_shape
if isinstance(height, str) or isinstance(width, str):  # Dimensiones dinámicas
    height, width = None, None

# Leer frame de entrada
frame = cv2.imread(INPUT_SOURCE) if isinstance(INPUT_SOURCE, str) else cv2.VideoCapture(INPUT_SOURCE).read()[1]
if frame is None:
    raise ValueError("No se pudo leer la imagen o fuente de video.")

# Conversión de canales si es necesario
if channels == 1:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Escala de grises
else:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Mantener RGB

# Redimensionar si el modelo tiene dimensiones fijas
if height and width:
    frame = cv2.resize(frame, (width, height))

# Normalizar (0-1)
frame = frame.astype(np.float32) / 255.0

# Ajustar forma para ONNX: (batch, canales, alto, ancho)
if channels == 1:
    frame = np.expand_dims(frame, axis=0)  # (1, alto, ancho)
else:
    frame = frame.transpose(2, 0, 1)  # (canales, alto, ancho)

frame = np.expand_dims(frame, axis=0)  # (batch, canales, alto, ancho)

# Inferencia
output = session.run(None, {input_name: frame})

# Procesar salida
result = output[0]
if result.ndim == 4 and result.shape[1] == 1:
    result = np.squeeze(result, axis=1)  # Quitar canal si es 1
elif result.ndim == 4:
    result = result.transpose(0, 2, 3, 1)  # Volver a HWC

# Convertir a formato visible
result = np.clip(result[0] * 255.0, 0, 255).astype(np.uint8)

# Guardar o mostrar
cv2.imwrite("resultado.png", cv2.cvtColor(result, cv2.COLOR_RGB2BGR) if channels != 1 else result)
print("[INFO] Resultado guardado como resultado.png")
