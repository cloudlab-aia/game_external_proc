#!/bin/bash
# Compila el interceptor LD_PRELOAD de glXSwapBuffers (formato shm con header).
# Genera dos nombres por compatibilidad con los scripts existentes:
#   wrapper_swapbuffers_shm.so  (pipeline/run_hybrid_pipeline.sh)
#   libswapcapture.so           (pipeline/run_ai_pipeline.sh, benchmarks/)
set -e
cd "$(dirname "$0")"

gcc -shared -fPIC -O2 -o wrapper_swapbuffers_shm.so wrapper_swapbuffers_shm.c -ldl -lGL
cp wrapper_swapbuffers_shm.so libswapcapture.so

echo "Compilado: capture/wrapper_swapbuffers_shm.so (alias libswapcapture.so)"
