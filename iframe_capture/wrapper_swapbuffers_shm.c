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

#define SHM_NAME "/framebuffer_shared"

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

    // Obtener tamaño dinámico del viewport
    GLint viewport[4];
    glGetIntegerv(GL_VIEWPORT, viewport);
    unsigned int width = viewport[2];
    unsigned int height = viewport[3];
    fprintf(stderr, "[WRAPPER] Tamaño de ventana: %dx%d\n", width, height);

    static int last_width = 0, last_height = 0;
    if (width != last_width || height != last_height) {
        printf("[wrapper_swapbuffers_shm] Cambio de tamaño detectado: %dx%d\n", width, height);
        last_width = width;
        last_height = height;
    }

    unsigned int frame_size = width * height * 4;
    int header_size = 8; // 2 x uint32_t
    int shm_total_size = header_size + frame_size;

    // Captura el frame
    unsigned char* pixels = malloc(frame_size);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    // Abre el segmento de memoria compartida
    int fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (fd < 0) {
        perror("shm_open");
        goto end;
    }

    fprintf(stderr, "[WRAPPER] Memoria compartida creada o encontrada.\n");

    // Ajusta el tamaño de la región compartida
    ftruncate(fd, shm_total_size);

    // Mapea la memoria
    void* shm_ptr = mmap(0, shm_total_size, PROT_WRITE, MAP_SHARED, fd, 0);
    if (shm_ptr == MAP_FAILED) {
        perror("mmap");
        goto close_fd;
    }

    // Escribir header (width, height)
    memcpy(shm_ptr, &width, 4);
    memcpy((char*)shm_ptr + 4, &height, 4);
    // Escribir framebuffer
    memcpy((char*)shm_ptr + header_size, pixels, frame_size);
    fprintf(stderr, "[WRAPPER] Frame y header copiados a memoria compartida.\n");

    // Desmapea y cierra
    munmap(shm_ptr, shm_total_size);

close_fd:
    close(fd);

end:
    free(pixels);
    real_glXSwapBuffers(dpy, drawable);
}
