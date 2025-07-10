#define _GNU_SOURCE
#include <GL/gl.h>
#include <GL/glx.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <string.h>

#define WIDTH 1920
#define HEIGHT 1080
#define SHM_NAME "/framebuffer_shared"
#define FRAME_SIZE (WIDTH * HEIGHT * 4)

static void (*real_glXSwapBuffers)(Display* dpy, GLXDrawable drawable) = NULL;

void glXSwapBuffers(Display* dpy, GLXDrawable drawable) {
    fprintf(stderr, "[WRAPPER] glXSwapBuffers interceptado.\n");
    
    if (!real_glXSwapBuffers) {
        real_glXSwapBuffers = dlsym(RTLD_NEXT, "glXSwapBuffers");
        if (!real_glXSwapBuffers) {
            fprintf(stderr, "Error al enlazar glXSwapBuffers\n");
            exit(1);
        }
    }

    // Captura el frame
    unsigned char* pixels = malloc(FRAME_SIZE);
    glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    // Abre el segmento de memoria compartida
    int fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (fd < 0) {
        perror("shm_open");
        goto end;
    }

    fprintf(stderr, "[WRAPPER] Memoria compartida creada o encontrada.\n");

    // Ajusta el tamaño de la región compartida
    ftruncate(fd, FRAME_SIZE);

    // Mapea la memoria
    void* shm_ptr = mmap(0, FRAME_SIZE, PROT_WRITE, MAP_SHARED, fd, 0);
    if (shm_ptr == MAP_FAILED) {
        perror("mmap");
        goto close_fd;
    }

    // Copia el frame a la memoria compartida
    memcpy(shm_ptr, pixels, FRAME_SIZE);
    fprintf(stderr, "[WRAPPER] Frame copiado a memoria compartida.\n");

    // Desmapea y cierra
    munmap(shm_ptr, FRAME_SIZE);

close_fd:
    close(fd);

end:
    free(pixels);
    real_glXSwapBuffers(dpy, drawable);
}
