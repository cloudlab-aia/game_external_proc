from pyvirtualdisplay import Display
import subprocess
import time
import numpy as np
import cv2
from easyprocess import EasyProcess

# Iniciar pantalla virtual
with Display(backend="xvfb", size=(1280, 720)) as disp:
    print(f"Ejecutando virtualmente en el DISPLAY={disp.display}")  # Para comprobar que se está ejecutando en la pantalla virtual

    # Ejecutar el juego en la pantalla virtual
    with EasyProcess(["/usr/games/sol"]) as proc:
        time.sleep(5)  # Esperar a que cargue el menú del juego para que no salga en negro

        # Capturar un frame del juego usando xwd
        subprocess.run(["xwd", "-display", f":{disp.display}", "-root", "-out", "screenshot.xwd"])

        # Convertir el archivo xwd a PNG usando ImageMagick (opcional)
        subprocess.run(["convert", "screenshot.xwd", "sol_frame.png"])

        print("Captura guardada como sol_frame.png")

