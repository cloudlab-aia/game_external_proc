# Real-ESRGAN Hybrid Architecture Analysis

**Analysis Date**: 2025-09-19T00:34:52.523898
**Architecture**: dGPU Rendering + iGPU AI Processing
**Total Experiments**: 15

## 🎯 Performance Summary

- **Average Native FPS**: 387.5 ± 456.9
- **Average Hybrid FPS**: 25.3 ± 30.8
- **Average Inference Latency**: 177.2 ± 208.3 ms
- **Average FPS Impact**: 93.9%

## 🏆 System Capabilities

- **Real-time Gaming (30+ FPS)**: 3/15 experiments (20.0%)
- **Competitive Gaming (60+ FPS)**: 3/15 experiments (20.0%)

## 💡 Recommendations

- ✅ Optimal resolutions for 60+ FPS: 320x240 (avg: 85 FPS)
- ⚠️ High latency - consider resolution reduction or model optimization
- ⚠️ Consider hardware upgrades or algorithm optimization

## 📊 Detailed Results

| Game | Resolution | Native FPS | Hybrid FPS | Inference (ms) | Impact (%) | Real-time |
|------|------------|------------|------------|----------------|------------|----------|
| Lightweight 3D (glxgears) | 320x240 | 1594.9 | 84.7 | 8.0 | 94.7% | ✅ |
| Lightweight 3D (glxgears) | 640x360 | 524.3 | 23.8 | 33.7 | 95.5% | ❌ |
| Lightweight 3D (glxgears) | 854x480 | 300.3 | 11.9 | 69.3 | 96.0% | ❌ |
| Lightweight 3D (glxgears) | 1280x720 | 130.9 | 4.2 | 201.8 | 96.8% | ❌ |
| Lightweight 3D (glxgears) | 1920x1080 | 58.5 | 1.5 | 559.3 | 97.4% | ❌ |
| Modern Game (AAA) | 320x240 | 644.7 | 85.1 | 8.0 | 86.8% | ✅ |
| Modern Game (AAA) | 640x360 | 218.9 | 24.4 | 32.9 | 88.9% | ❌ |
| Modern Game (AAA) | 854x480 | 122.2 | 11.9 | 69.7 | 90.3% | ❌ |
| Modern Game (AAA) | 1280x720 | 54.8 | 4.1 | 203.1 | 92.4% | ❌ |
| Modern Game (AAA) | 1920x1080 | 23.9 | 1.4 | 586.9 | 94.0% | ❌ |
| Competitive Game (esports) | 320x240 | 1308.5 | 85.0 | 8.0 | 93.5% | ✅ |
| Competitive Game (esports) | 640x360 | 430.9 | 23.8 | 33.7 | 94.5% | ❌ |
| Competitive Game (esports) | 854x480 | 245.8 | 11.7 | 70.5 | 95.2% | ❌ |
| Competitive Game (esports) | 1280x720 | 105.5 | 4.1 | 205.3 | 96.1% | ❌ |
| Competitive Game (esports) | 1920x1080 | 47.7 | 1.5 | 567.9 | 96.9% | ❌ |
