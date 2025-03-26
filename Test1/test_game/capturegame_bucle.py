from pyvirtualdisplay import Display
import subprocess
import time
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
from easyprocess import EasyProcess

# Crear la carpeta "frames" si no existe
output_dir = "frames"
os.makedirs(output_dir, exist_ok=True)

# Iniciar pantalla virtual usando Xephyr
with Display(backend="xephyr", size=(1280, 720), visible=True) as disp:
    print(f"Ejecutando en DISPLAY={disp.display}")

    # Ejecutar el juego en la pantalla virtual
    with EasyProcess(["/usr/games/supertuxkart"]) as proc:
        time.sleep(5)  # Esperar a que cargue un poco

        # Bucle de captura y actualización
        frame_count = 0
        while True:
            # Registrar el tiempo de inicio
            start_time = time.time()

            # Capturar un frame del juego usando xwd
            xwd_file = os.path.join(output_dir, f"frame_{frame_count}.xwd")
            png_file = os.path.join(output_dir, f"frame_{frame_count}.png")
            subprocess.run(["xwd", "-display", f":{disp.display}", "-root", "-out", xwd_file])

            # Convertir el archivo xwd a PNG usando ImageMagick
            subprocess.run(["convert", xwd_file, png_file])

            # Registrar el tiempo de finalización
            end_time = time.time()

            # Calcular la latencia
            latency = end_time - start_time
            print(f"Frame capturado: {png_file} | Latencia: {latency:.4f} segundos")

            frame_count += 1

            # Esperar un tiempo antes de capturar el siguiente frame
            time.sleep(1)
