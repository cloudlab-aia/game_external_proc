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
GLuint tex;

void initSharedMemory() {
    size_t buffer_size = WIDTH * HEIGHT * 4;
    shm_fd = shm_open(SHM_NAME, O_RDONLY, 0666);
    shared_mem = (unsigned char*) mmap(0, buffer_size, PROT_READ, MAP_SHARED, shm_fd, 0);
    if (shared_mem == MAP_FAILED) {
        perror("mmap"); exit(1);
    }
}

void initPipe() {
    pipe_fd = open(PIPE_NAME, O_RDONLY);
}

void initTexture() {
    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, shared_mem);
}

void display() {
    char signal;
    if (read(pipe_fd, &signal, 1) > 0) {
        glBindTexture(GL_TEXTURE_2D, tex);
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, shared_mem);

        glClear(GL_COLOR_BUFFER_BIT);
        glEnable(GL_TEXTURE_2D);
        glBegin(GL_QUADS);
            glTexCoord2f(0, 0); glVertex2f(-1, -1);
            glTexCoord2f(1, 0); glVertex2f(1, -1);
            glTexCoord2f(1, 1); glVertex2f(1, 1);
            glTexCoord2f(0, 1); glVertex2f(-1, 1);
        glEnd();
        glDisable(GL_TEXTURE_2D);
        glutSwapBuffers();
    }
    glutPostRedisplay();
}

int main(int argc, char** argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA);
    glutInitWindowSize(WIDTH, HEIGHT);
    glutCreateWindow("GPU2 - Procesamiento");

    initSharedMemory();
    initPipe();
    initTexture();

    glutDisplayFunc(display);
    glutMainLoop();
    return 0;
}
