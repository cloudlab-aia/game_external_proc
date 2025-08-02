#!/usr/bin/env python3
"""
Setup script for RealESRGAN ONNX model
This script will either create a symbolic link to an existing model or help set up the proper model
"""

import os
import shutil

def setup_realesrgan_model():
    """Setup RealESRGAN ONNX model"""
    
    # Check if we have the target file
    target_file = "RealESRGAN_x4.onnx"
    
    # Available models in the directory
    available_models = [
        "super-resolution-10.onnx",
        "single-image-super-resolution-1032.xml"  # OpenVINO format
    ]
    
    if os.path.exists(target_file):
        print(f"{target_file} already exists!")
        return True
    
    # Check if we have super-resolution-10.onnx and use it as a fallback
    if os.path.exists("super-resolution-10.onnx"):
        print("Using super-resolution-10.onnx as RealESRGAN_x4.onnx")
        shutil.copy("super-resolution-10.onnx", target_file)
        print(f"Created {target_file} from super-resolution-10.onnx")
        return True
    
    print("No suitable ONNX model found!")
    print("Available files:")
    for file in os.listdir("."):
        if file.endswith(('.onnx', '.pth', '.xml')):
            print(f"  - {file}")
    
    return False

def download_realesrgan_onnx():
    """Try to download RealESRGAN ONNX from various sources"""
    import urllib.request
    
    urls = [
        # Try various sources
        "https://github.com/onnx/models/raw/main/vision/super_resolution/sub_pixel_cnn_2016/model/super-resolution-10.onnx",
        "https://media.githubusercontent.com/media/onnx/models/main/vision/super_resolution/sub_pixel_cnn_2016/model/super-resolution-10.onnx"
    ]
    
    for url in urls:
        try:
            print(f"Trying to download from: {url}")
            urllib.request.urlretrieve(url, "downloaded_model.onnx")
            
            # If successful, rename it
            if os.path.exists("downloaded_model.onnx"):
                os.rename("downloaded_model.onnx", "RealESRGAN_x4.onnx")
                print("Successfully downloaded and set up RealESRGAN_x4.onnx")
                return True
                
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    
    return False

if __name__ == "__main__":
    print("Setting up RealESRGAN ONNX model...")
    
    # First try to use existing models
    if setup_realesrgan_model():
        print("Model setup complete!")
    else:
        print("Trying to download a suitable model...")
        if download_realesrgan_onnx():
            print("Download and setup complete!")
        else:
            print("Failed to set up model. You may need to manually convert or download the model.")
            print("Try running: pip install torch basicsr realesrgan")
            print("Then run the convert_realesrgan.py script")
