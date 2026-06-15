// game_launch_interposer.c
//
// Se precarga (LD_PRELOAD) sobre el LAUNCHER de Minecraft, que se ejecuta con
// normalidad en el display real. Intercepta las llamadas de lanzamiento de
// procesos (execve/execvp/posix_spawn...) y, SOLO cuando detecta que el
// launcher arranca el juego (la JVM con "net.minecraft" en los argumentos),
// reescribe el entorno de ESE proceso hijo para que:
//   - su ventana vaya a la pantalla virtual (DISPLAY = GAME_VIRT_DISPLAY)
//   - VirtualGL renderice en la dGPU (VGL_DISPLAY) y capture el frame
//     (LD_PRELOAD = GAME_VGL_PRELOAD, LD_LIBRARY_PATH = GAME_VGL_LDPATH)
//   - se quite WAYLAND_DISPLAY para forzar X11
// El resto de procesos del launcher se lanzan sin tocar.
//
// Variables que debe aportar el lanzador (ver pipeline/run_minecraft_virtualscreen.sh):
//   GAME_VIRT_DISPLAY, GAME_VGL_DISPLAY, GAME_VGL_PRELOAD, GAME_VGL_LDPATH
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <spawn.h>
#include <unistd.h>

extern char **environ;

static int is_game(char *const argv[]) {
    if (!argv) return 0;
    for (int i = 0; argv[i]; i++)
        if (strstr(argv[i], "net.minecraft") || strstr(argv[i], "minecraft.client"))
            return 1;
    return 0;
}

// Devuelve un envp nuevo (malloc) con las claves indicadas sustituidas/añadidas.
static char **rewrite_env(char *const base[]) {
    static const char *keys[] = {"DISPLAY=", "VGL_DISPLAY=", "LD_PRELOAD=",
                                 "LD_LIBRARY_PATH=", "WAYLAND_DISPLAY="};
    const int NK = 5;

    const char *vdisp = getenv("GAME_VIRT_DISPLAY");
    const char *vgld  = getenv("GAME_VGL_DISPLAY");
    const char *vpre  = getenv("GAME_VGL_PRELOAD");
    const char *vldp  = getenv("GAME_VGL_LDPATH");
    if (!vdisp) vdisp = ":2";
    if (!vgld)  vgld  = ":1";

    int n = 0;
    while (base && base[n]) n++;
    char **out = malloc(sizeof(char *) * (n + 8));
    int o = 0;
    for (int i = 0; i < n; i++) {
        int skip = 0;
        for (int k = 0; k < NK; k++)
            if (strncmp(base[i], keys[k], strlen(keys[k])) == 0) { skip = 1; break; }
        if (!skip) out[o++] = base[i];
    }
    char buf[8192];
    snprintf(buf, sizeof(buf), "DISPLAY=%s", vdisp);        out[o++] = strdup(buf);
    snprintf(buf, sizeof(buf), "VGL_DISPLAY=%s", vgld);     out[o++] = strdup(buf);
    if (vpre) { snprintf(buf, sizeof(buf), "LD_PRELOAD=%s", vpre); out[o++] = strdup(buf); }
    if (vldp) { snprintf(buf, sizeof(buf), "LD_LIBRARY_PATH=%s", vldp); out[o++] = strdup(buf); }
    // WAYLAND_DISPLAY se omite (ya filtrada arriba)
    out[o] = NULL;
    fprintf(stderr, "[INTERPOSER] Juego detectado → pantalla virtual %s (VGL en %s)\n", vdisp, vgld);
    return out;
}

static int (*real_execve)(const char *, char *const[], char *const[]) = NULL;
static int (*real_posix_spawn)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                               const posix_spawnattr_t *, char *const[], char *const[]) = NULL;
static int (*real_posix_spawnp)(pid_t *, const char *, const posix_spawn_file_actions_t *,
                                const posix_spawnattr_t *, char *const[], char *const[]) = NULL;

static void init(void) {
    if (!real_execve) real_execve = dlsym(RTLD_NEXT, "execve");
    if (!real_posix_spawn) real_posix_spawn = dlsym(RTLD_NEXT, "posix_spawn");
    if (!real_posix_spawnp) real_posix_spawnp = dlsym(RTLD_NEXT, "posix_spawnp");
}

int execve(const char *path, char *const argv[], char *const envp[]) {
    init();
    if (is_game(argv)) return real_execve(path, argv, rewrite_env(envp));
    return real_execve(path, argv, envp);
}

// execv/execvp/execvpe usan environ; los redirigimos a execve con env reescrito si es el juego.
int execv(const char *path, char *const argv[]) {
    init();
    return execve(path, argv, environ);
}
int execvp(const char *file, char *const argv[]) {
    init();
    if (is_game(argv) && strchr(file, '/'))
        return real_execve(file, argv, rewrite_env(environ));
    int (*r)(const char *, char *const[]) = dlsym(RTLD_NEXT, "execvp");
    return r(file, argv);
}
int execvpe(const char *file, char *const argv[], char *const envp[]) {
    init();
    if (is_game(argv) && strchr(file, '/'))
        return real_execve(file, argv, rewrite_env(envp));
    int (*r)(const char *, char *const[], char *const[]) = dlsym(RTLD_NEXT, "execvpe");
    return r(file, argv, envp);
}

int posix_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *fa,
                const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    init();
    if (is_game(argv)) return real_posix_spawn(pid, path, fa, attr, argv, rewrite_env(envp));
    return real_posix_spawn(pid, path, fa, attr, argv, envp);
}
int posix_spawnp(pid_t *pid, const char *file, const posix_spawn_file_actions_t *fa,
                 const posix_spawnattr_t *attr, char *const argv[], char *const envp[]) {
    init();
    if (is_game(argv)) return real_posix_spawnp(pid, file, fa, attr, argv, rewrite_env(envp));
    return real_posix_spawnp(pid, file, fa, attr, argv, envp);
}
