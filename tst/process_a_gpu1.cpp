// ======================
// PROCESO A: GPU1 (captura)
// Archivo: process_a_gpu1.cpp
// ======================
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <GL/glut.h>
#include <GL/gl.h>
#include <iostream>
#include <cstring>

#define WIDTH 1280
#define HEIGHT 720
#define SHM_NAME "/my_frame_buffer"
#define PIPE_NAME "/tmp/frame_signal_pipe"

unsigned char* shared_mem = nullptr;
int shm_fd;
int pipe_fd;

void initSharedMemory() {
    size_t buffer_size = WIDTH * HEIGHT * 4;
    shm_fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    ftruncate(shm_fd, buffer_size);
    shared_mem = (unsigned char*) mmap(0, buffer_size, PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (shared_mem == MAP_FAILED) {
        perror("mmap"); exit(1);
    }
}

void initPipe() {
    mkfifo(PIPE_NAME, 0666);
    pipe_fd = open(PIPE_NAME, O_WRONLY);
}

void display() {
    glClear(GL_COLOR_BUFFER_BIT);

    // Simula el contenido de frame
    glBegin(GL_TRIANGLES);
    glColor3f(1.0, 0.0, 0.0); glVertex2f(-1.0, -1.0);
    glColor3f(0.0, 1.0, 0.0); glVertex2f(1.0, -1.0);
    glColor3f(0.0, 0.0, 1.0); glVertex2f(0.0, 1.0);
    glEnd();
    glFlush();

    glReadBuffer(GL_FRONT);
    glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, shared_mem);
    char signal = 1;
    write(pipe_fd, &signal, 1);
    usleep(16000);  // ~60 FPS
    glutPostRedisplay();
}

int main(int argc, char** argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB);
    glutInitWindowSize(WIDTH, HEIGHT);
    glutCreateWindow("GPU1 - Captura");

    initSharedMemory();
    initPipe();

    glutDisplayFunc(display);
    glutMainLoop();

    return 0;
}