#!/bin/bash
#gcc -shared -fPIC -o wrapper_swapbuffers.so wrapper_swapbuffers.c -ldl -lGL
gcc -shared -fPIC -o wrapper_swapbuffers_shm.so wrapper_swapbuffers_shm.c -ldl -lGL
if [ $? -ne 0 ]; then
    echo "ERROR: Falló la compilación de wrapper_swapbuffers_shm.so"
    exit 1
fi
echo "Compilado: wrapper_swapbuffers.so"
