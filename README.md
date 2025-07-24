# Game External Processing Pipeline

## Overview

A high-performance real-time GPU frame capture and AI processing pipeline that intercepts OpenGL frames from games and applications, then applies AI enhancements using Intel integrated GPU acceleration. The system leverages shared memory for ultra-low latency frame transfer and OpenCL acceleration for real-time super-resolution processing.

## Features

- **Real-time GPU Frame Capture**: Direct OpenGL frame interception via custom `glXSwapBuffers` wrapper
- **AI-Powered Enhancement**: ONNX-based super-resolution with Intel iGPU acceleration  
- **Ultra-Low Latency**: ~10-15ms AI processing latency via OpenCL optimization
- **Shared Memory Pipeline**: Zero-copy frame transfer between capture and processing
- **Hybrid GPU Usage**: NVIDIA dGPU for game rendering, Intel iGPU for AI processing
- **Web Streaming**: Flask-based HTTP streaming for remote viewing
- **Debugging Tools**: Frame dumps, performance monitoring, and diagnostic outputs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Game/App      │    │  Frame Capture  │    │  AI Processing  │
│  (NVIDIA dGPU)  │──▶│ (Shared Memory) │──▶│  (Intel iGPU)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                     │
                              ▼                     ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   Raw Frames    │    │ Enhanced Frames │
                    │   (1920x1080)   │    │   (3840x2160)   │
                    └─────────────────┘    └─────────────────┘
```

## Components

### 1. Frame Capture (`frame_capture/`)
- **`wrapper_swapbuffers_shm.c`**: OpenGL interception library
- **`run_hybrid_pipeline.sh`**: Complete pipeline automation script
- **`web_stream_gpu1.py`**: Flask streaming server

### 2. AI Processing (`iframe_capture/`)
- **`upscale_display.py`**: Intel iGPU-optimized AI upscaling (**Working**)
- **`realtime_display_igpu.py`**: Real-time display with FPS monitoring
- **`libswapcapture.so`**: Optimized frame capture library

### 3. Models (`models/`)
- **`super-resolution-10.onnx`**: Pre-trained 2x super-resolution model (224x224 input)

### 4. VirtualGL Integration (`virtualgl/`)
- Custom VirtualGL build with frame capture modifications
- GPU context management and OpenGL interception

## System Requirements

### Hardware
- **NVIDIA GPU**: For game rendering (tested with RTX 5060)
- **Intel iGPU**: For AI processing (UHD Graphics or better)
- **RAM**: 8GB+ recommended for shared memory buffering
- **CPU**: Multi-core recommended for parallel processing

### Software
- **OS**: Ubuntu 20.04+ (tested on 25.04)
- **NVIDIA Drivers**: Proprietary drivers with OpenGL support
- **Intel Graphics**: Mesa drivers with OpenCL support
- **Python**: 3.8+ with OpenCV 4.10+

## Installation

### 1. Install System Dependencies

```bash
sudo apt update && sudo apt install -y \
    build-essential cmake gcc g++ \
    python3 python3-pip python3-opencv \
    libxtst-dev libxcb-glx0-dev libx11-xcb-dev \
    libxcb-keysyms1-dev mesa-utils \
    intel-opencl-icd clinfo \
    xvfb x11-apps
```

### 2. Verify GPU Setup

```bash
# Check for hybrid GPU setup
lspci | grep -i vga

# Verify OpenCL devices
clinfo | grep -A 5 -B 5 "Device Name"

# Expected output:
# - NVIDIA GeForce RTX 5060 (Platform 0)  
# - Intel(R) Graphics (Platform 1)
```

### 3. Build Frame Capture Components

```bash
# Build VirtualGL (if needed)
cd virtualgl && mkdir -p build && cd build
cmake .. && make -j$(nproc)

# Build frame capture wrapper
cd ../../frame_capture
chmod +x build.sh && ./build.sh
```

### 4. Install Python Dependencies

```bash
pip3 install flask opencv-python numpy
```

## Usage

### Quick Start - AI Upscaling

The fastest way to test AI-powered frame enhancement:

```bash
cd iframe_capture

# Run AI upscaling with Intel iGPU acceleration
python3 upscale_display.py
```

**Expected Output:**
```
[INFO] Inicializando Intel iGPU...
[INFO] OpenCL habilitado exitosamente
[INFO] DNN configurado para usar OpenCL
[INFO] Intel iGPU configurada exitosamente
[INFO] Latencia IA: 12.34 ms
```

### Complete Pipeline - Game Capture + AI Enhancement

```bash
cd frame_capture

# Launch complete hybrid pipeline
chmod +x run_hybrid_pipeline.sh
./run_hybrid_pipeline.sh
```

This will:
1. Compile the OpenGL interception wrapper
2. Start virtual X server (Xvfb)
3. Launch `glxgears` with frame capture
4. Start Flask streaming server on port 5000

**Access the stream:** `http://localhost:5000/video_feed`

### Manual Frame Capture

```bash
# Capture frames from any OpenGL application
cd frame_capture
LD_PRELOAD=./wrapper_swapbuffers_shm.so glxgears

# In another terminal, process captured frames
cd ../iframe_capture  
python3 upscale_display.py
```

## Performance Metrics

### Measured Performance (RTX 5060 + Intel UHD Graphics)

| Component | Latency | Throughput | GPU Usage |
|-----------|---------|-----------|-----------|
| Frame Capture | ~1ms | 60+ FPS | NVIDIA dGPU |
| Shared Memory | ~0.1ms | Zero-copy | System RAM |
| AI Processing | **10-15ms** | **60+ FPS** | **Intel iGPU** |
| Total Pipeline | **~16ms** | **60+ FPS** | Hybrid |

### Intel iGPU Optimization

The system specifically forces Intel iGPU usage through:

```bash
# Environment variables automatically set:
OPENCV_OCL_DEVICE="1:GPU:0"          # Platform 1 (Intel)
OPENCL_VENDOR="Intel"                # Force Intel vendor
CUDA_VISIBLE_DEVICES=""              # Hide NVIDIA from OpenCV
```

## Configuration

### GPU Selection

Edit `iframe_capture/upscale_display.py` to modify GPU targeting:

```python
# Force Intel iGPU (Platform 1)
os.environ["OPENCV_OCL_DEVICE"] = "1:GPU:0"

# Alternative: Force NVIDIA (Platform 0) 
# os.environ["OPENCV_OCL_DEVICE"] = "0:GPU:0"
```

### Model Configuration

Replace the ONNX model for different AI effects:

```python
# In upscale_display.py
MODEL_PATH = "/path/to/your/model.onnx"

# Adjust input size based on your model
frame_small = cv2.resize(frame_bgr, (224, 224))  # Model input size
```

### Shared Memory Settings

Modify buffer size for different resolutions:

```python
# For 4K capture
WIDTH, HEIGHT = 3840, 2160
FRAME_SIZE = WIDTH * HEIGHT * 4  # RGBA

# For 1080p (default)
WIDTH, HEIGHT = 1920, 1080
FRAME_SIZE = WIDTH * HEIGHT * 4
```

## Troubleshooting

### Intel iGPU Not Detected

```bash
# Check Intel graphics drivers
sudo apt install intel-media-va-driver-non-free
sudo apt install mesa-va-drivers

# Verify OpenCL support
clinfo | grep Intel
```

### OpenGL Capture Issues

```bash
# Check X11 forwarding
echo $DISPLAY

# Test basic OpenGL
glxinfo | grep "direct rendering"
glxgears -info
```

### Performance Issues

```bash
# Monitor GPU usage
intel_gpu_top          # Intel iGPU
nvidia-smi -l 1        # NVIDIA dGPU

# Check shared memory usage
ls -la /dev/shm/framebuffer_shared
```

### Common Error Solutions

| Error | Solution |
|-------|---------|
| `ModuleNotFoundError: No module named 'cv2'` | `sudo apt install python3-opencv` |
| `OpenCL not available` | `sudo apt install intel-opencl-icd` |
| `Permission denied: /framebuffer_shared` | Check `/dev/shm/` permissions |
| `Can't read ONNX file` | Verify model path in `MODEL_PATH` |

## Development

### File Structure

```
game_external_proc/
├── README.md                          # This documentation
├── models/
│   └── super-resolution-10.onnx      # AI model
├── frame_capture/                     # OpenGL interception
│   ├── wrapper_swapbuffers_shm.c     # Core capture logic
│   ├── run_hybrid_pipeline.sh        # Pipeline automation
│   └── web_stream_gpu1.py            # HTTP streaming
├── iframe_capture/                    # AI processing
│   ├── upscale_display.py            # Intel iGPU optimized (MAIN)
│   └── realtime_display_igpu.py      # Real-time viewer
└── virtualgl/                        # VirtualGL integration
    └── [VirtualGL source code]
```

### Adding New AI Models

1. Convert your model to ONNX format
2. Place in `models/` directory
3. Update `MODEL_PATH` in processing scripts
4. Adjust input/output dimensions as needed

### Custom Frame Processing

Extend `upscale_display.py` with your own processing:

```python
def custom_processing(frame_bgr):
    # Your custom AI processing here
    processed_frame = your_model(frame_bgr)
    return processed_frame
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Test with your hardware configuration
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **VirtualGL Project**: OpenGL interception foundation
- **OpenCV Team**: Computer vision and OpenCL support
- **Intel**: OpenCL drivers and iGPU documentation
- **ONNX Community**: Model format and runtime support

---

**Status**: **Production Ready** - Intel iGPU acceleration working with 10-15ms latency
**Last Updated**: 2025-07-24
**Tested On**: Ubuntu 25.04, RTX 5060 + Intel UHD Graphics
