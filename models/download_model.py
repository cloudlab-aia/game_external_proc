#!/usr/bin/env python3
"""
Script to download FSRCNN pre-trained model for super-resolution
"""
import urllib.request
import os

def download_fsrcnn_model():
    """Download FSRCNN x2 model from OpenCV's model zoo"""
    
    model_url = "https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x2.pb"
    model_path = "FSRCNN_x2.pb"
    
    if os.path.exists(model_path):
        print(f"[INFO] Model {model_path} already exists, skipping download.")
        return model_path
    
    print(f"[INFO] Downloading FSRCNN model from {model_url}")
    print("[INFO] This may take a few moments...")
    
    try:
        urllib.request.urlretrieve(model_url, model_path)
        print(f"[INFO] Model downloaded successfully: {model_path}")
        print(f"[INFO] File size: {os.path.getsize(model_path) / 1024:.1f} KB")
        return model_path
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        return None

def download_alternative_models():
    """Download additional models if needed"""
    models = {
        "FSRCNN_x3.pb": "https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x3.pb",
        "FSRCNN_x4.pb": "https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x4.pb"
    }
    
    for model_name, url in models.items():
        if not os.path.exists(model_name):
            try:
                print(f"[INFO] Downloading {model_name}...")
                urllib.request.urlretrieve(url, model_name)
                print(f"[INFO] {model_name} downloaded successfully")
            except Exception as e:
                print(f"[WARN] Failed to download {model_name}: {e}")

if __name__ == "__main__":
    print("Downloading FSRCNN Super-Resolution Models")
    print("=" * 50)
    
    # Download main model (x2 scale)
    main_model = download_fsrcnn_model()
    
    if main_model:
        print(f"\nMain model ready: {main_model}")
        
        # Ask if user wants additional models
        response = input("\n📥 Download additional models (x3, x4)? [y/N]: ").lower()
        if response in ['y', 'yes']:
            download_alternative_models()
    
    print("\nSetup complete! You can now run the super-resolution script.")
