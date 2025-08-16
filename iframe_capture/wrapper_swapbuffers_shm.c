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

    // Asegurar que OpenGL terminó de dibujar
    glFinish();

    // Obtener viewport real
    GLint viewport[4];
    glGetIntegerv(GL_VIEWPORT, viewport);
    unsigned int width = (unsigned int)viewport[2];
    unsigned int height = (unsigned int)viewport[3];
    if (width == 0 || height == 0) goto call_real;

    glPixelStorei(GL_PACK_ALIGNMENT, 1);

    const int header_size = 16;
    uint32_t frame_size = width * height * 4u;
    off_t shm_total_size = header_size + frame_size;

    unsigned char *pixels = (unsigned char*)malloc(frame_size);
    if (!pixels) goto call_real;

    int retry = 0;
    int success = 0;
    while(retry < 3 && !success) {
        glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
        // Verificar si frame no es completamente negro
        unsigned char sum = 0;
        for(int i=0; i<frame_size; i+=4) sum += pixels[i]+pixels[i+1]+pixels[i+2];
        if(sum > 0) success = 1;
        else retry++;
    }

    if(!success) {
        free(pixels);
        goto call_real;
    }

    int fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if(fd < 0) { free(pixels); goto call_real; }
    if(ftruncate(fd, shm_total_size) < 0) { close(fd); free(pixels); goto call_real; }

    void *shm_ptr = mmap(NULL, shm_total_size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if(shm_ptr == MAP_FAILED) { close(fd); free(pixels); goto call_real; }

    uint32_t *header = (uint32_t*)shm_ptr;
    header[0] = width;
    header[1] = height;
    static uint32_t seq_counter = 0;
    seq_counter++;
    header[2] = seq_counter;
    header[3] = 0; // escribiendo

    unsigned char *shm_fb = (unsigned char*)shm_ptr + header_size;
    size_t row_bytes = (size_t)width*4u;

    for(unsigned int r=0; r<height; ++r) {
        unsigned char *src = pixels + r*row_bytes;
        unsigned char *dst = shm_fb + (size_t)(height-1-r)*row_bytes;
        memcpy(dst, src, row_bytes);
    }

    msync(shm_ptr, shm_total_size, MS_SYNC);
    header[3] = 1;
    msync(shm_ptr, header_size, MS_SYNC);

    munmap(shm_ptr, shm_total_size);
    close(fd);
    free(pixels);

call_real:
    real_glXSwapBuffers(dpy, drawable);
}
