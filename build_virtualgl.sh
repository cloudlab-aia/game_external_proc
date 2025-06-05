#!/bin/bash
set -e

echo "[INFO] Building VirtualGL from source inside virtualgl/build"

cd "$(dirname "$0")/virtualgl"

mkdir -p build
cd build
cmake ..
make -j$(nproc)

echo "[SUCCESS] VirtualGL built successfully."
