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
#define HEADER_SIZE 16

// Cache de memoria compartida
static struct {
    void* ptr;
    size_t size;
    int fd;
    uint32_t width, height;
} shm_cache = {NULL, 0, -1, 0, 0};

static void (*real_glXSwapBuffers)(Display* dpy, GLXDrawable drawable) = NULL;
static unsigned char *pixels = NULL;
static size_t pixels_size = 0;

static inline int setup_shm(uint32_t width, uint32_t height) {
    uint32_t frame_size = width * height * 4;
    size_t total_size = HEADER_SIZE + frame_size;
    
    // Reutilizar si el tamaño coincide
    if (shm_cache.ptr && shm_cache.size == total_size && 
        shm_cache.width == width && shm_cache.height == height) {
        return 1;
    }
    
    // Limpiar cache anterior
    if (shm_cache.ptr) {
        munmap(shm_cache.ptr, shm_cache.size);
        close(shm_cache.fd);
    }
    
    // Reasignar buffer de pixels si es necesario
    if (pixels_size < frame_size) {
        free(pixels);
        pixels = malloc(frame_size);
        if (!pixels) return 0;
        pixels_size = frame_size;
    }
    
    shm_cache.fd = shm_open(SHM_NAME, O_CREAT | O_RDWR, 0666);
    if (shm_cache.fd < 0) return 0;
    
    if (ftruncate(shm_cache.fd, total_size) < 0) {
        close(shm_cache.fd);
        return 0;
    }
    
    shm_cache.ptr = mmap(NULL, total_size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_cache.fd, 0);
    if (shm_cache.ptr == MAP_FAILED) {
        close(shm_cache.fd);
        return 0;
    }
    
    shm_cache.size = total_size;
    shm_cache.width = width;
    shm_cache.height = height;
    return 1;
}

void glXSwapBuffers(Display* dpy, GLXDrawable drawable) {
    if (!real_glXSwapBuffers) {
        real_glXSwapBuffers = dlsym(RTLD_NEXT, "glXSwapBuffers");
        if (!real_glXSwapBuffers) {
            fprintf(stderr, "Error al enlazar glXSwapBuffers: %s\n", dlerror());
            exit(1);
        }
    }

    glFinish();
    
    GLint viewport[4];
    glGetIntegerv(GL_VIEWPORT, viewport);
    uint32_t width = (uint32_t)viewport[2];
    uint32_t height = (uint32_t)viewport[3];
    
    if (width == 0 || height == 0 || !setup_shm(width, height)) {
        goto call_real;
    }

    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    // Verificación rápida de frame negro (solo primeros 1024 pixels)
    uint32_t quick_sum = 0;
    int check_pixels = (width * height > 1024) ? 1024 : width * height;
    for (int i = 0; i < check_pixels * 4; i += 16) {
        quick_sum |= *((uint32_t*)(pixels + i));
    }
    
    if (quick_sum == 0) goto call_real;

    uint32_t *header = (uint32_t*)shm_cache.ptr;
    header[0] = width;
    header[1] = height;
    static uint32_t seq_counter = 0;
    header[2] = ++seq_counter;
    header[3] = 0; // escribiendo

    // Copia con flip vertical optimizada
    unsigned char *shm_fb = (unsigned char*)shm_cache.ptr + HEADER_SIZE;
    size_t row_bytes = width * 4;
    
    for (uint32_t r = 0; r < height; ++r) {
        memcpy(shm_fb + (height - 1 - r) * row_bytes, 
               pixels + r * row_bytes, 
               row_bytes);
    }

    header[3] = 1; // listo
    // Usar MS_ASYNC para no bloquear
    msync(shm_cache.ptr, HEADER_SIZE, MS_ASYNC);

call_real:
    real_glXSwapBuffers(dpy, drawable);
}
