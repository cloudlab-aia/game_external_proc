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
#include <time.h>

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

// --- Interposición de dlsym / glXGetProcAddress ---
// LWJGL3/GLFW (Minecraft >= 1.13) no llama a glXSwapBuffers por enlace
// dinámico normal: carga libGL con dlopen() y resuelve los símbolos con
// dlsym() o glXGetProcAddressARB(), lo que se saltaría un LD_PRELOAD
// clásico. Interceptamos también esas rutas de resolución para devolver
// nuestro wrapper en su lugar.

typedef void (*GLXFuncPtr)(void);

void glXSwapBuffers(Display* dpy, GLXDrawable drawable);
GLXFuncPtr glXGetProcAddressARB(const GLubyte *procName);

static void *(*real_dlsym)(void *, const char *) = NULL;

static int init_real_dlsym(void) {
    if (real_dlsym) return 1;
    // glibc moderna (>= 2.34) integra libdl en libc; la versión del símbolo
    // sigue siendo la histórica en x86_64. Probar ambas por compatibilidad.
    real_dlsym = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.2.5");
    if (!real_dlsym) real_dlsym = dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.34");
    if (!real_dlsym)
        fprintf(stderr, "[WRAPPER] No se pudo resolver dlsym real\n");
    return real_dlsym != NULL;
}

void *dlsym(void *handle, const char *symbol) {
    if (!init_real_dlsym()) return NULL;
    if (symbol) {
        if (strcmp(symbol, "glXSwapBuffers") == 0)
            return (void *)glXSwapBuffers;
        if (strcmp(symbol, "glXGetProcAddress") == 0 ||
            strcmp(symbol, "glXGetProcAddressARB") == 0)
            return (void *)glXGetProcAddressARB;
    }
    return real_dlsym(handle, symbol);
}

GLXFuncPtr glXGetProcAddressARB(const GLubyte *procName) {
    static GLXFuncPtr (*real_gpa)(const GLubyte *) = NULL;
    if (procName && strcmp((const char *)procName, "glXSwapBuffers") == 0)
        return (GLXFuncPtr)glXSwapBuffers;
    if (!real_gpa) {
        if (!init_real_dlsym()) return NULL;
        real_gpa = (GLXFuncPtr (*)(const GLubyte *))
            real_dlsym(RTLD_NEXT, "glXGetProcAddressARB");
        if (!real_gpa) return NULL;
    }
    return real_gpa(procName);
}

GLXFuncPtr glXGetProcAddress(const GLubyte *procName) {
    return glXGetProcAddressARB(procName);
}

// --- Filtro por proceso ---
// Con LD_PRELOAD sobre un launcher, TODOS sus procesos hijos heredan el
// wrapper. Si más de uno hace swaps (launcher CEF + juego), ambos escriben
// en la misma shm con tamaños distintos y el ftruncate de uno invalida el
// mapeo del otro (SIGBUS). FRAME_CAPTURE_EXE limita la captura al proceso
// cuyo nombre contenga la subcadena indicada (p. ej. "java" = solo el juego).
static int capture_enabled(void) {
    static int checked = 0, enabled = 1;
    if (!checked) {
        checked = 1;
        const char *want = getenv("FRAME_CAPTURE_EXE");
        if (want && *want) {
            char comm[64] = {0};
            FILE *f = fopen("/proc/self/comm", "r");
            if (f) {
                if (!fgets(comm, sizeof(comm), f)) comm[0] = 0;
                fclose(f);
            }
            comm[strcspn(comm, "\n")] = 0;
            enabled = (strstr(comm, want) != NULL);
            fprintf(stderr, "[WRAPPER] proceso '%s': captura %s\n",
                    comm, enabled ? "ACTIVA" : "desactivada");
        }
    }
    return enabled;
}

// Modo "capturar sin presentar": tras capturar el frame de la VRAM, NO se llama
// al swap real, evitando la presentación (en Xvfb la copia software es el cuello
// copy-bound). Así la dGPU renderiza el siguiente frame de inmediato (GPU-bound)
// y el frame queda oculto de verdad (nunca se muestra). Activar con
// CAPTURE_SKIP_PRESENT=1. Solo aplica cuando la captura ha tenido éxito.
static int skip_present(void) {
    static int checked = 0, skip = 0;
    if (!checked) {
        checked = 1;
        const char *v = getenv("CAPTURE_SKIP_PRESENT");
        skip = (v && *v && *v != '0');
    }
    return skip;
}

// Sello de tiempo de captura en un buzón APARTE (/framebuffer_ts, 16 bytes:
// uint32 seq, 4 de relleno, uint64 nanosegundos CLOCK_MONOTONIC). No toca el
// formato del frame. Lo lee el medidor de latencia para calcular el tiempo
// captura→pantalla. CLOCK_MONOTONIC es comparable entre procesos.
static void *ts_ptr = NULL;
static void write_capture_ts(uint32_t seq) {
    if (!ts_ptr) {
        int fd = shm_open("/framebuffer_ts", O_CREAT | O_RDWR, 0666);
        if (fd < 0) return;
        if (ftruncate(fd, 16) == 0)
            ts_ptr = mmap(NULL, 16, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        close(fd);
        if (ts_ptr == MAP_FAILED) { ts_ptr = NULL; return; }
    }
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    uint64_t ns = (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
    *((uint32_t*)ts_ptr) = seq;
    *((uint64_t*)((char*)ts_ptr + 8)) = ns;
}

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
        // Usar real_dlsym directamente: nuestro dlsym interceptado devolvería
        // este mismo wrapper y causaría recursión infinita.
        if (!init_real_dlsym()) exit(1);
        real_glXSwapBuffers = real_dlsym(RTLD_NEXT, "glXSwapBuffers");
        if (!real_glXSwapBuffers) {
            fprintf(stderr, "Error al enlazar glXSwapBuffers: %s\n", dlerror());
            exit(1);
        }
    }

    if (!capture_enabled()) goto call_real;

    glFinish();

    // Tamaño del drawable (ventana), no del viewport: juegos como Minecraft
    // cambian glViewport varias veces por frame (GUI, passes intermedios) y
    // en el swap el viewport puede no coincidir con la ventana.
    uint32_t width = 0, height = 0;
    unsigned int qw = 0, qh = 0;
    glXQueryDrawable(dpy, drawable, GLX_WIDTH, &qw);
    glXQueryDrawable(dpy, drawable, GLX_HEIGHT, &qh);
    width = (uint32_t)qw;
    height = (uint32_t)qh;
    if (width == 0 || height == 0) {
        GLint viewport[4];
        glGetIntegerv(GL_VIEWPORT, viewport);
        width = (uint32_t)viewport[2];
        height = (uint32_t)viewport[3];
    }

    if (width == 0 || height == 0 || !setup_shm(width, height)) {
        goto call_real;
    }

    // Leer SIEMPRE del framebuffer de la ventana: motores como Photon/Iris
    // pueden dejar un FBO intermedio enlazado en el momento del swap, y
    // glReadPixels leería ese buffer (vacío) en lugar del frame real.
    #ifndef GL_READ_FRAMEBUFFER
    #define GL_READ_FRAMEBUFFER 0x8CA8
    #endif
    #ifndef GL_READ_FRAMEBUFFER_BINDING
    #define GL_READ_FRAMEBUFFER_BINDING 0x8CAA
    #endif
    static void (*p_glBindFramebuffer)(GLenum, GLuint) = NULL;
    if (!p_glBindFramebuffer) {
        if (!init_real_dlsym()) goto call_real;
        GLXFuncPtr (*gpa)(const GLubyte *) =
            real_dlsym(RTLD_NEXT, "glXGetProcAddressARB");
        if (gpa)
            p_glBindFramebuffer = (void (*)(GLenum, GLuint))
                gpa((const GLubyte *)"glBindFramebuffer");
    }
    GLint prev_read_fbo = 0;
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &prev_read_fbo);
    if (prev_read_fbo != 0 && p_glBindFramebuffer)
        p_glBindFramebuffer(GL_READ_FRAMEBUFFER, 0);

    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    if (prev_read_fbo != 0 && p_glBindFramebuffer)
        p_glBindFramebuffer(GL_READ_FRAMEBUFFER, (GLuint)prev_read_fbo);

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
    write_capture_ts(seq_counter);   // sello de tiempo para medir latencia
    // Usar MS_ASYNC para no bloquear
    msync(shm_cache.ptr, HEADER_SIZE, MS_ASYNC);

    // Capturado de VRAM; si se pide, NO presentar (oculto de verdad + GPU-bound).
    if (skip_present()) return;

call_real:
    real_glXSwapBuffers(dpy, drawable);
}
