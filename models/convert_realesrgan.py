#!/usr/bin/env python3
"""
Script to convert RealESRGAN PyTorch model to ONNX format
This script requires torch, basicsr, and realesrgan packages
"""

import os
import torch
import onnx
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet

def convert_realesrgan_to_onnx():
    """Convert RealESRGAN PyTorch model to ONNX format"""
    
    # Model parameters for RealESRGAN x4plus
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    
    # Load the pre-trained weights
    netscale = 4
    model_path = 'RealESRGAN_x4plus.pth'
    
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found!")
        return False
    
    # Load the model weights
    loadnet = torch.load(model_path, map_location=torch.device('cpu'))
    if 'params_ema' in loadnet:
        keyname = 'params_ema'
    else:
        keyname = 'params'
    model.load_state_dict(loadnet[keyname], strict=True)
    model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(1, 3, 64, 64)  # Batch size 1, 3 channels, 64x64 image
    
    # Export to ONNX
    output_path = 'RealESRGAN_x4.onnx'
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size', 2: 'height', 3: 'width'},
            'output': {0: 'batch_size', 2: 'height', 3: 'width'}
        }
    )
    
    print(f"Successfully converted to {output_path}")
    return True

if __name__ == "__main__":
    try:
        convert_realesrgan_to_onnx()
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please install required packages:")
        print("pip install torch basicsr realesrgan")
    except Exception as e:
        print(f"Conversion failed: {e}")
