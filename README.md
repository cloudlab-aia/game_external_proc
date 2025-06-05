# game_external_proc

## Overview

This project captures frames directly from the GPU in real-time and processes them externally to the native rendering pipeline. By leveraging GPU capabilities and advanced frame processing, it aims to enhance rendering performance, reduce latency, and enable image enhancements such as upscaling or frame interpolation.

## Features

- **GPU Frame Capture:** Uses VirtualGL to intercept and capture GPU-rendered frames.
- **Frame Processing Pipeline:** Processes frames with CPU, iGPU, or NPU for optimization or enhancements.
- **Low Latency:** Designed to minimize capture and processing latency for real-time use.
- **Debugging Tools:** Provides debug outputs and frame dumps for development and validation.
- **Cross-platform Support:** Developed and tested on Ubuntu with NVIDIA GPUs; broader compatibility planned.

## Motivation

Modern games and graphics applications often require advanced post-processing for better visuals or performance. External frame capture enables custom enhancements without modifying the game or rendering engine. This project explores methods and feasibility for such integration.

## Current Status

- Functional prototype capturing frames via VirtualGL.
- Custom `glXSwapBuffers` modifications for frame capture and debugging.
- Basic debug output and frame dumps implemented.
- Active development for improved stability and features.

## Getting Started

### System Requirements

- Ubuntu (tested on 20.04+)
- NVIDIA GPU with proprietary drivers installed
- Intel iGPU recommended for processing
- Development tools: CMake, GCC/G++, make

### Required Packages

Install all necessary dependencies:

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    gcc \
    g++ \
    libxtst-dev \
    libxcb-glx0-dev \
    libx11-xcb-dev \
    libxcb-keysyms1-dev \
    mesa-utils
```   
### Building the Project

```bash
cd /home/octa/Escritorio/game_external_proc/virtualgl
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Running

Use vglrun (built in virtualgl/build/bin/vglrun) to launch your OpenGL application with frame capture enabled:

```bash
./virtualgl/build/bin/vglrun glxgears
```
```bash
./virtualgl/build/bin/vglrun ./your_opengl_application
```
Captured frames and debug output will be saved to /tmp/.

## Verification & Debugging

Check if your system has both an Intel iGPU and NVIDIA dGPU:

```bash
lspci | grep -i vga
```

Expected output or similar:

```
00:02.0 VGA compatible controller: Intel Corporation UHD Graphics 630
01:00.0 VGA compatible controller: NVIDIA Corporation TU116 [GeForce GTX 1660 SUPER]
```
This confirms that your system has a hybrid GPU setup, allowing capture with the NVIDIA dGPU and processing with the Intel iGPU.

## Development Notes

Make sure you have all dependencies installed using the instructions above in the **Required Packages** section.

VirtualGL is already included locally in the `virtualgl/` directory. You do **not** need to install it system-wide. Just run:

```bash
./build_virtualgl.sh
```

This builds VirtualGL in a local `virtualgl/build` directory.
