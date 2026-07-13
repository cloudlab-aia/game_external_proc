#define _GNU_SOURCE
#include <GL/gl.h>
#include <GL/glx.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static void (*real_glXSwapBuffers)(Display* dpy, GLXDrawable drawable) = NULL;

void glXSwapBuffers(Display* dpy, GLXDrawable drawable) {
    if (!real_glXSwapBuffers) {
        real_glXSwapBuffers = dlsym(RTLD_NEXT, "glXSwapBuffers");
        if (!real_glXSwapBuffers) {
            fprintf(stderr, "Error: no se pudo cargar glXSwapBuffers real\n");
            exit(1);
        }
    }

    int width = 1920;
    int height = 1080;
    unsigned char* pixels = malloc(width * height * 4);

    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    FILE* f = fopen("/tmp/frame.raw", "wb");
    if (f) {
        fwrite(pixels, 1, width * height * 4, f);
        fclose(f);
        fprintf(stderr, "[wrapper] Frame capturado en /tmp/frame.raw\n");
    } else {
        fprintf(stderr, "[wrapper] No se pudo abrir /tmp/frame.raw\n");
    }

    free(pixels);
    real_glXSwapBuffers(dpy, drawable);
}
