import os
import struct
import time
import cv2
import numpy as np
import openvino as ov

# Configuración
SHM_NAME = "/dev/shm/framebuffer_shared"
# Header del wrapper (capture/wrapper_swapbuffers_shm.c):
# uint32 width, height, seq, ready — seguido del frame RGBA ya volteado
HEADER_FMT = "IIII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_DIM = 8192  # sanidad: descartar headers corruptos
MODEL_XML = "/home/ogg/Desktop/AIA/game_external_proc/models/single-image-super-resolution-1032.xml"
MODEL_BIN = "/home/ogg/Desktop/AIA/game_external_proc/models/single-image-super-resolution-1032.bin"

# Inicializar OpenVINO
core = ov.Core()

# Mostrar dispositivos disponibles
print("[INFO] Dispositivos disponibles:", core.available_devices)

# Intentar usar GPU (iGPU Intel) si está disponible, sino CPU optimizado
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
else:  # CPU optimizations
    # Configuración simplificada para Core Ultra 7 265K
    import os
    num_cores = os.cpu_count()
    config["CACHE_DIR"] = "/tmp/openvino_cache"
    print(f"[INFO] Configuración CPU: {num_cores} núcleos disponibles")
    
compiled_model = core.compile_model(model=model, device_name=device, config=config)

# Obtener información de inputs y outputs
input_layers = [compiled_model.input(i) for i in range(len(compiled_model.inputs))]
output_layer = compiled_model.output(0)

print(f"[INFO] Modelo cargado con {len(input_layers)} entradas:")
for i, inp in enumerate(input_layers):
    print(f"  Input {i}: {inp.shape}")
print(f"[INFO] Output: {output_layer.shape}")

def preprocess_frame(frame):
    """Prepara el frame en dos resoluciones para el modelo ESPCN:
    - Input 0: Imagen de baja resolución (270x480)
    - Input 1: Imagen de alta resolución original (1080x1920)
    """
    # Convertir a RGB
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Entrada 0: Baja resolución (270x480)
    lr_img = cv2.resize(img_rgb, (480, 270))  # Width x Height
    lr_blob = lr_img.transpose(2, 0, 1)  # HWC → CHW
    lr_blob = lr_blob[np.newaxis, :, :, :].astype(np.float32) / 255.0
    
    # Entrada 1: Alta resolución (1080x1920) - imagen original
    hr_img = cv2.resize(img_rgb, (1920, 1080))  # Asegurar tamaño correcto
    hr_blob = hr_img.transpose(2, 0, 1)  # HWC → CHW  
    hr_blob = hr_blob[np.newaxis, :, :, :].astype(np.float32) / 255.0
    
    return lr_blob, hr_blob

def postprocess(residual, hr_blob):
    """Convierte la salida del modelo a imagen BGR.

    El modelo single-image-super-resolution-1032 devuelve un RESIDUO de alta
    frecuencia (media ≈0); la imagen final es ese residuo sumado a la entrada
    bicúbica (input 1). Usar la salida directamente da una imagen casi negra.
    """
    sr = (residual + hr_blob)[0].transpose(1, 2, 0)  # CHW → HWC
    out_img = (sr * 255.0).clip(0, 255).astype(np.uint8)
    return cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)

def upscale_frame(frame_bgr):
    """Aplica superresolución usando el modelo de dos entradas (LR + bicúbica)"""
    lr_blob, hr_blob = preprocess_frame(frame_bgr)

    # Preparar las entradas como diccionario usando los nombres de los inputs
    inputs = {
        input_layers[0]: lr_blob,  # Baja resolución
        input_layers[1]: hr_blob   # Alta resolución de referencia (bicúbica)
    }

    # Ejecutar inferencia → residuo, que se suma a la bicúbica
    result = compiled_model(inputs)[output_layer]
    return postprocess(result, hr_blob)

_last_seq = 0

def get_shared_frame():
    """Lee un frame nuevo de la memoria compartida (formato con header).

    Devuelve None si no hay frame nuevo (mismo seq) o si la shm no existe aún.
    El wrapper ya escribe el frame volteado (origen arriba-izquierda): no
    hace falta flip.
    """
    global _last_seq
    try:
        fd = os.open(SHM_NAME, os.O_RDONLY)
        try:
            header = os.read(fd, HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                return None
            width, height, seq, ready = struct.unpack(HEADER_FMT, header)
            if not ready or seq == _last_seq:
                return None
            if not (0 < width <= MAX_DIM and 0 < height <= MAX_DIM):
                return None
            buf = os.read(fd, width * height * 4)
            if len(buf) < width * height * 4:
                return None
        finally:
            os.close(fd)
        _last_seq = seq
        frame = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    except FileNotFoundError:
        return None
    except Exception as e:
        print("[WARN] Error al leer frame compartido:", e)
        return None

# === Bucle principal ===
if __name__ == "__main__":
    print("[INFO] Esperando frames desde memoria compartida...")
    print("[INFO] Pulsa 'q' en la ventana de IA para salir.")
    
    # Crear ventana una sola vez con título fijo
    window_title = f"AI Upscaling (ESPCN + OpenVINO) - {device}"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    # Mover al monitor de la iGPU si se especifica su posición X
    igpu_x = int(os.environ.get("IGPU_MONITOR_X", 0))
    cv2.moveWindow(window_title, igpu_x, 0)
    cv2.setWindowProperty(window_title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    frame_count = 0
    total_latency = 0
    
    while True:
        frame = get_shared_frame()
        if frame is None:
            time.sleep(0.01)
            continue
            
        try:
            start = time.time()
            frame_up = upscale_frame(frame)
            latency = (time.time() - start) * 1000
            
            # Estadísticas cada 30 frames
            frame_count += 1
            total_latency += latency
            
            if frame_count % 30 == 0:
                avg_latency = total_latency / 30
                fps = 1000 / avg_latency if avg_latency > 0 else 0
                print(f"[INFO] Frame {frame_count}: Latencia promedio: {avg_latency:.2f} ms (~{fps:.1f} FPS) - Última latencia: {latency:.1f}ms")
                total_latency = 0
                
            # Mostrar frame en la ventana existente
            cv2.imshow(window_title, frame_up)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        except Exception as e:
            print(f"[ERROR] Error en procesamiento: {e}")
            time.sleep(0.1)

    cv2.destroyAllWindows()
