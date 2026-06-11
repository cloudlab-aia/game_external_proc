from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import time

window = 0

def draw_circle(radius):
    glBegin(GL_LINE_LOOP)
    for i in range(360):
        angle = math.radians(i)
        glVertex2f(math.cos(angle) * radius, math.sin(angle) * radius)
    glEnd()

def draw_hand(angle, length, width):
    glLineWidth(width)
    glBegin(GL_LINES)
    glVertex2f(0.0, 0.0)
    glVertex2f(length * math.cos(math.radians(angle)),
               length * math.sin(math.radians(angle)))
    glEnd()

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()

    # Dibujar el borde del reloj
    glColor3f(1.0, 1.0, 1.0)
    draw_circle(0.9)

    # Marcas del reloj
    for i in range(12):
        angle = math.radians(i * 30)
        x = 0.8 * math.cos(angle)
        y = 0.8 * math.sin(angle)
        glPointSize(4)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    # Obtener hora actual
    t = time.localtime()
    seconds = t.tm_sec
    minutes = t.tm_min
    hours = t.tm_hour % 12 + minutes / 60.0

    # Dibujar agujas (sentido antihorario)
    glColor3f(1.0, 0.0, 0.0)  # Horas - rojo
    draw_hand(90 + hours * 30, 0.5, 4)

    glColor3f(0.0, 1.0, 0.0)  # Minutos - verde
    draw_hand(90 + minutes * 6, 0.7, 2)

    glColor3f(0.0, 0.5, 1.0)  # Segundos - azul
    draw_hand(90 + seconds * 6, 0.8, 1)

    glutSwapBuffers()

def timer(value):
    glutPostRedisplay()
    glutTimerFunc(1000, timer, 0)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutInitWindowSize(640, 640)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Reloj Analogico OpenGL")
    glutDisplayFunc(display)
    glutTimerFunc(0, timer, 0)
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(-1.0, 1.0, -1.0, 1.0)
    glutMainLoop()

if __name__ == "__main__":
    main()
