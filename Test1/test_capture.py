from pyvirtualdisplay import Display
import numpy as np
import cv2
import pyglet
from OpenGL.GL import *  # OpenGL con PyOpenGL

# Iniciar pantalla virtual
display = Display(visible=0, size=(800, 600))
display.start()

# Crear ventana OpenGL en la pantalla virtual
config = pyglet.gl.Config(double_buffer=True)
window = pyglet.window.Window(800, 600, config=config)

# Función para renderizar un frame OpenGL
def render_frame():
    glClearColor(0.0, 0.0, 0.0, 1.0)  # Fondo negro
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # Asegurar que se usa el color azul antes de empezar a dibujar
    glColor3f(1.0, 0.0, 0.0)  # azul

    # Dibujar un cuadrado azul
    glBegin(GL_QUADS)
    glVertex2f(-0.5, -0.5)
    glVertex2f(0.5, -0.5)
    glVertex2f(0.5, 0.5)
    glVertex2f(-0.5, 0.5)
    glEnd()
    
    window.flip()  # Enviar a la pantalla virtual

# Renderizar y capturar un frame
render_frame()

# Capturar la imagen del framebuffer
buffer = (GLubyte * (800 * 600 * 3))()
glReadPixels(0, 0, 800, 600, GL_RGB, GL_UNSIGNED_BYTE, buffer)
image = np.frombuffer(buffer, dtype=np.uint8).reshape((600, 800, 3))
image = cv2.flip(image, 0)  # OpenGL invierte la imagen

# Guardar el frame capturado
cv2.imwrite("captured_frame.png", image)

# Finalizar
window.close()
display.stop()

print("Frame capturado y guardado como 'captured_frame.png'")
