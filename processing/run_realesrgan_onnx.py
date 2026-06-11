import onnxruntime as ort
import numpy as np
from PIL import Image
import cv2

# Carga la imagen de entrada (usa tu propio frame aquí)
input_img = Image.open("input.png").convert("RGB")
img = np.array(input_img).astype(np.float32) / 255.0
img = np.transpose(img, (2, 0, 1))[None, ...]  # NCHW

# Carga el modelo ONNX
session = ort.InferenceSession("RealESRGAN_x4.onnx", providers=['CPUExecutionProvider'])

# Ejecuta la inferencia
outputs = session.run(None, {"input": img})
out_img = outputs[0][0]
out_img = np.clip(out_img, 0, 1)
out_img = (out_img * 255).astype(np.uint8)
out_img = np.transpose(out_img, (1, 2, 0))  # HWC

# Muestra el resultado
cv2.imshow("RealESRGAN Output", out_img)
cv2.waitKey(0)
cv2.destroyAllWindows()