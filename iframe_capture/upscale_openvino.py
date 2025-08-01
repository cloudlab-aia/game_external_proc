import os
import cv2
import time
import numpy as np
import cv2.dnn_superres as dnn_sr

# Configuración del frame
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
SHM_NAME = "/dev/shm/framebuffer_shared"

# Ruta al modelo OpenVINO IR
MODEL_XML = "../models/single-image-super-resolution-1032.xml"
MODEL_BIN = "../models/single-image-super-resolution-1032.bin"

# === Inicializar OpenCV DNN Super Resolution ===
try:
    sr = dnn_sr.DnnSuperResImpl_create()
    
    # Choose upscaling factor: 2, 3, or 4
    UPSCALE_FACTOR = 4  # Change to 2, 3, or 4 as needed

    model_path = f"FSRCNN_x{UPSCALE_FACTOR}.pb"
    sr.readModel(model_path)
    sr.setModel("fsrcnn", UPSCALE_FACTOR)
    
    print(f"[INFO] FSRCNN x{UPSCALE_FACTOR} model loaded: {model_path}")
    print("[INFO] Optimized for low latency gaming!")
    
except Exception as e:
    print(f"[ERROR] Failed to load FSRCNN model: {e}")
    print("[INFO] Please run: python3 download_model.py")
    exit(1)

# === Leer de memoria compartida ===
def get_shared_frame():
    try:
        fd = os.open(SHM_NAME, os.O_RDONLY)
        buf = os.read(fd, FRAME_SIZE)
        os.close(fd)
        print("Buffer size:", len(buf))  # Debe ser 1920*1080*4 = 8,294,400 bytes
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((HEIGHT, WIDTH, 4))
        # The frame is RGBA, take only RGB channels and keep as RGB
        frame_rgb = frame[:, :, :3]
        # Convert RGB to BGR for OpenCV display
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        frame_bgr = cv2.flip(frame_bgr, 0)
        return frame_bgr
    except Exception as e:
        print("[WARN] Error al leer frame compartido:", e)
        return None

# === Aplicar superresolución optimizada ===
def upscale_openvino(frame_bgr):
    try:
        # Para mejor calidad: usar la mayor resolución posible como entrada
        # Si el modelo x4 está cargado, la entrada puede ser 480x270, pero mejor usar 960x540 si el rendimiento lo permite
        input_size = (WIDTH // 4, HEIGHT // 4)  # 480x270 para 1920x1080
        frame_small = cv2.resize(frame_bgr, input_size)

        # Aplicar FSRCNN x4 directamente (480x270 -> 1920x1080)
        upscaled = sr.upsample(frame_small)

        # Si el modelo x4 está bien, el resultado ya es 1920x1080, no hace falta bicubic
        return upscaled
        
    except Exception as e:
        print(f"[ERROR] Fallo en superresolución: {e}")
        # Fallback: simple bicubic upscaling
        return cv2.resize(frame_bgr, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)

# === Bucle principal ===
if __name__ == "__main__":
    print("[INFO] Mostrando ventana OpenVINO con IA. Pulsa 'q' para salir.")
    
    # Configurar ventana principal
    window_name = "AI Super-Resolution (FSRCNN x2|3|4) - 1920x1080"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, WIDTH, HEIGHT)  # Tamaño igual que glxgears (1920x1080)
    
    # Opcional: centrar la ventana (puede no funcionar en todos los WM)
    try:
        cv2.moveWindow(window_name, 100, 100)  # Posición inicial
    except:
        pass
    while True:
        frame = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
        try:
            start = time.time()
            upscaled = upscale_openvino(frame)
            latency = (time.time() - start) * 1000
            print(f"[INFO] Latencia IA: {latency:.2f} ms")
            
            # Debug: Print frame and upscaled shapes occasionally
            if np.random.random() < 0.05:  # 5% of the time
                print(f"[DEBUG] Original frame shape: {frame.shape}")
                print(f"[DEBUG] Upscaled frame shape: {upscaled.shape}")
                print(f"[DEBUG] Original frame min/max: {frame.min()}/{frame.max()}")
                print(f"[DEBUG] Upscaled frame min/max: {upscaled.min()}/{upscaled.max()}")

            # Mostrar resultado de IA en tamaño completo 1920x1080
            cv2.imshow(window_name, upscaled)
            cv2.imshow("Original Frame", frame)
            
            # Opcional: mostrar comparación pequeña para debug
            # if np.random.random() < 0.02:  # Solo 2% del tiempo para no saturar
            #     original_small = cv2.resize(frame, (480, 270))
            #     upscaled_small = cv2.resize(upscaled, (480, 270))
            #     comparison = cv2.hconcat([original_small, upscaled_small])
            #     cv2.imshow("Debug: Original vs AI (small)", comparison)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("[ERROR] Fallo durante inferencia:", e)
            time.sleep(0.1)

    cv2.destroyAllWindows()
