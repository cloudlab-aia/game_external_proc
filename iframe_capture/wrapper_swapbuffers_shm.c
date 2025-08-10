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
#include <sys/stat.h>
#include <errno.h>
#include <stdint.h>

#define SHM_NAME "/framebuffer_shared"

static void (*real_glXSwapBuffers)(Display* dpy, GLXDrawable drawable) = NULL;

void glXSwapBuffers(Display* dpy, GLXDrawable drawable) {
    if (!real_glXSwapBuffers) {
        real_glXSwapBuffers = dlsym(RTLD_NEXT, "glXSwapBuffers");
        if (!real_glXSwapBuffers) {
            fprintf(stderr, "Error al enlazar glXSwapBuffers: %s\n", dlerror());
            exit(1);
        }
    }

    // Obtener viewport
    GLint viewport[4];
    glGetIntegerv(GL_VIEWPORT, viewport);
    unsigned int width = (unsigned int)viewport[2];
    unsigned int height = (unsigned int)viewport[3];

    // Ajustes para lectura (evitar padding)
    glPixelStorei(GL_PACK_ALIGNMENT, 1);

    // Header: width (u32), height (u32), seq (u32), ready (u32)
    const int header_size = 16;
    uint32_t frame_size = width * height * 4u;
    off_t shm_total_size = header_size + frame_size;

    // Reservar buffer de lectura
    unsigned char *pixels = (unsigned char*)malloc(frame_size);
    if (!pixels) {
        fprintf(stderr, "[WRAPPER] malloc failed\n");
        goto call_real;
    }

    // Leer pixels (origin: bottom-left)
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    // Open or create shared memory
    int fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (fd < 0) {
        fprintf(stderr, "[WRAPPER] shm_open error: %s\n", strerror(errno));
        goto free_pixels;
    }

    // Resize shared memory
    if (ftruncate(fd, shm_total_size) < 0) {
        fprintf(stderr, "[WRAPPER] ftruncate error: %s\n", strerror(errno));
        goto close_fd;
    }

    // Map shared memory
    void *shm_ptr = mmap(NULL, shm_total_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (shm_ptr == MAP_FAILED) {
        fprintf(stderr, "[WRAPPER] mmap error: %s\n", strerror(errno));
        goto close_fd;
    }

    // Prepare header: set ready=0 first
    uint32_t *header = (uint32_t*)shm_ptr;
    header[0] = width;
    header[1] = height;
    static uint32_t seq_counter = 0;
    seq_counter++;
    header[2] = seq_counter;
    header[3] = 0; // ready = 0 (escribiendo)

    // Puntero al framebuffer dentro del shm (top-down)
    unsigned char *shm_fb = (unsigned char*)shm_ptr + header_size;

    // Escribir filas en orden invertido para que el lector tenga top-down
    // pixels contiene rows bottom-up, cada row = width * 4 bytes
    size_t row_bytes = (size_t)width * 4u;
    for (unsigned int r = 0; r < height; ++r) {
        // fuente: row r from bottom => pixels + r*row_bytes
        // destino: row (height-1 - r) to get top-down
        unsigned char *src = pixels + r * row_bytes;
        unsigned char *dst = shm_fb + (size_t)(height - 1 - r) * row_bytes;
        memcpy(dst, src, row_bytes);
    }

    // msync para asegurar escritura visible
    if (msync(shm_ptr, shm_total_size, MS_SYNC) < 0) {
        fprintf(stderr, "[WRAPPER] msync error: %s\n", strerror(errno));
    }

    // Marcar ready = 1 y volver a msync solo para el header (optimización)
    header[3] = 1;
    if (msync(shm_ptr, header_size, MS_SYNC) < 0) {
        fprintf(stderr, "[WRAPPER] msync header error: %s\n", strerror(errno));
    }

    // Unmap and close
    munmap(shm_ptr, shm_total_size);

close_fd:
    close(fd);
free_pixels:
    free(pixels);
call_real:
    // Llamada original
    real_glXSwapBuffers(dpy, drawable);
}
