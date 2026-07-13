#define _GNU_SOURCE
#include <GL/glx.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <string.h>
#include <time.h>

static void (*real_glXSwapBuffers)(Display* dpy, GLXDrawable drawable) = NULL;
static int width = 0, height = 0;
static int shm_fd = -1;
static unsigned char *shm_ptr = NULL;
static size_t shm_size = 0;

static void init_shm(int w, int h) {
    if (shm_fd != -1) {
        munmap(shm_ptr, shm_size);
        close(shm_fd);
    }

    shm_size = w * h * 4 + sizeof(int) * 2;
    shm_fd = shm_open("/framebuffer_shared", O_CREAT | O_RDWR, 0666);
    ftruncate(shm_fd, shm_size);
    shm_ptr = mmap(0, shm_size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);

    memcpy(shm_ptr, &w, sizeof(int));
    memcpy(shm_ptr + sizeof(int), &h, sizeof(int));
}

void glXSwapBuffers(Display* dpy, GLXDrawable drawable) {
    if (!real_glXSwapBuffers) {
        real_glXSwapBuffers = dlsym(RTLD_NEXT, "glXSwapBuffers");
    }

    if (width == 0 || height == 0) {
        XWindowAttributes gwa;
        XGetWindowAttributes(dpy, drawable, &gwa);
        width = gwa.width;
        height = gwa.height;
        init_shm(width, height);
        fprintf(stderr, "[Wrapper] Capturando resolución: %dx%d\n", width, height);
    }

    glReadBuffer(GL_FRONT);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, shm_ptr + sizeof(int) * 2);

    real_glXSwapBuffers(dpy, drawable);
}
