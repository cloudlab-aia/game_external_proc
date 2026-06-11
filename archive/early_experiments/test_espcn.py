#!/usr/bin/env python3
import cv2
import numpy as np
import openvino as ov
import time

# Configuración
MODEL_XML = "/home/ogg/Desktop/AIA/game_external_proc/models/single-image-super-resolution-1032.xml"
MODEL_BIN = "/home/ogg/Desktop/AIA/game_external_proc/models/single-image-super-resolution-1032.bin"

def test_espcn_model():
    """Prueba el modelo ESPCN con una imagen sintética"""
    
    # Inicializar OpenVINO
    core = ov.Core()
    
    print("[INFO] Dispositivos disponibles:", core.available_devices)
    
    # Intentar usar GPU (iGPU Intel) si está disponible
    device = "GPU" if "GPU" in core.available_devices else "CPU"
    print(f"[INFO] Usando dispositivo: {device}")
    
    # Cargar modelo
    print(f"[INFO] Cargando modelo: {MODEL_XML}")
    model = core.read_model(model=MODEL_XML, weights=MODEL_BIN)
    
    # Configurar para optimizar rendimiento
    config = {}
    if device == "GPU":
        config["GPU_DISABLE_WINOGRAD_CONVOLUTION"] = "YES"
        config["CACHE_DIR"] = "/tmp/openvino_cache"
        
    compiled_model = core.compile_model(model=model, device_name=device, config=config)
    
    # Obtener información de inputs y outputs
    input_layers = [compiled_model.input(i) for i in range(len(compiled_model.inputs))]
    output_layer = compiled_model.output(0)
    
    print(f"[INFO] Modelo cargado con {len(input_layers)} entradas:")
    for i, inp in enumerate(input_layers):
        print(f"  Input {i}: {inp.shape}")
    print(f"[INFO] Output: {output_layer.shape}")
    
    # Crear imagen sintética para prueba (1920x1080)
    print("[INFO] Creando imagen sintética de prueba...")
    test_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # Dibujar algunos patrones para que sea visible el resultado
    cv2.rectangle(test_image, (100, 100), (500, 400), (255, 0, 0), -1)  # Rectángulo azul
    cv2.rectangle(test_image, (600, 200), (1000, 500), (0, 255, 0), -1)  # Rectángulo verde
    cv2.rectangle(test_image, (1100, 300), (1500, 600), (0, 0, 255), -1)  # Rectángulo rojo
    cv2.putText(test_image, "TEST ESPCN", (200, 800), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 3)
    
    def preprocess_frame(frame):
        """Prepara el frame en dos resoluciones para el modelo ESPCN"""
        # Convertir a RGB
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Entrada 0: Baja resolución (270x480)
        lr_img = cv2.resize(img_rgb, (480, 270))
        lr_blob = lr_img.transpose(2, 0, 1)  # HWC → CHW
        lr_blob = lr_blob[np.newaxis, :, :, :].astype(np.float32) / 255.0
        
        # Entrada 1: Alta resolución (1080x1920)
        hr_img = cv2.resize(img_rgb, (1920, 1080))
        hr_blob = hr_img.transpose(2, 0, 1)  # HWC → CHW  
        hr_blob = hr_blob[np.newaxis, :, :, :].astype(np.float32) / 255.0
        
        return lr_blob, hr_blob
    
    def postprocess(output):
        """Convierte la salida del modelo a imagen BGR"""
        out_img = output[0].transpose(1, 2, 0)  # CHW → HWC
        out_img = (out_img * 255.0).clip(0, 255).astype(np.uint8)
        img_bgr = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
        return img_bgr
    
    # Procesar la imagen
    print("[INFO] Procesando imagen con IA...")
    start_time = time.time()
    
    lr_blob, hr_blob = preprocess_frame(test_image)
    
    # Preparar las entradas
    inputs = {
        input_layers[0]: lr_blob,  # Baja resolución 
        input_layers[1]: hr_blob   # Alta resolución de referencia
    }
    
    # Ejecutar inferencia
    result = compiled_model(inputs)[output_layer]
    processed_image = postprocess(result)
    
    latency = (time.time() - start_time) * 1000
    print(f"[INFO] Latencia IA: {latency:.2f} ms")
    
    # Mostrar resultados
    print("[INFO] Mostrando resultado. Presiona 'q' para salir.")
    
    while True:
        # Mostrar imagen original y procesada lado a lado
        display_original = cv2.resize(test_image, (960, 540))  # Reducir a la mitad
        display_processed = cv2.resize(processed_image, (960, 540))  # Reducir a la mitad
        
        # Concatenar horizontalmente
        combined = np.hstack([display_original, display_processed])
        
        # Añadir texto
        cv2.putText(combined, "Original", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(combined, "ESPCN Enhanced", (1010, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.imshow("Test ESPCN Model", combined)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    print("[INFO] Prueba completada.")

if __name__ == "__main__":
    test_espcn_model()
