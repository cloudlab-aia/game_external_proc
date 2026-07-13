#!/usr/bin/env python3
"""
Test script for RealESRGAN ONNX model
"""

import numpy as np
import onnxruntime as ort

MODEL_ONNX = "/home/ogg/Desktop/AIA/game_external_proc/models/RealESRGAN_x4.onnx"

def test_model():
    """Test the ONNX model with dummy input"""
    try:
        # Load model
        ort_session = ort.InferenceSession(MODEL_ONNX, providers=['CPUExecutionProvider'])
        print(f"[INFO] Model loaded successfully: {MODEL_ONNX}")
        
        # Get input/output info
        input_name = ort_session.get_inputs()[0].name
        input_shape = ort_session.get_inputs()[0].shape
        output_name = ort_session.get_outputs()[0].name
        output_shape = ort_session.get_outputs()[0].shape
        
        print(f"Input name: {input_name}")
        print(f"Input shape: {input_shape}")
        print(f"Output name: {output_name}")
        print(f"Output shape: {output_shape}")
        
        # Create dummy input (224x224 grayscale image)
        dummy_input = np.random.rand(1, 1, 224, 224).astype(np.float32)
        print(f"Dummy input shape: {dummy_input.shape}")
        
        # Run inference
        outputs = ort_session.run(None, {input_name: dummy_input})
        
        print(f"Output tensor shape: {outputs[0].shape}")
        print(f"Output min/max: {outputs[0].min():.3f} / {outputs[0].max():.3f}")
        
        print("[SUCCESS] Model test completed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Model test failed: {e}")
        return False

if __name__ == "__main__":
    test_model()
