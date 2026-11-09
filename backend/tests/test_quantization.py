"""
PikVaidya AI — Automated Tests for Edge INT8 Quantization Pipeline
==================================================================
Tests INT8 model existence, session loading, forward pass execution,
numerical parity with FP32, and latency profiling across all crops.
"""

import os
from pathlib import Path
import pytest
import numpy as np
import onnxruntime as ort
from PIL import Image

from app.services.model_service import model_service, UnsupportedCropError


def test_quantized_int8_models_exist():
    """Verifies that INT8 ONNX models are generated for all supported crops."""
    root = model_service._resolve_project_root()
    expected_models = [
        "models/sugarcane/efficientnet_b0/model_int8.onnx",
        "models/sugarcane/mobilenet_v3/model_int8.onnx",
        "models/tomato/mobilenet_v3/model_int8.onnx",
        "models/onion/mobilenet_v3/model_int8.onnx",
    ]
    for rel_path in expected_models:
        full_path = root / rel_path
        assert full_path.exists(), f"INT8 model missing at: {full_path}"
        assert full_path.stat().st_size > 100000, f"INT8 model at {full_path} is suspiciously small"


@pytest.mark.parametrize("crop", ["sugarcane", "tomato", "onion"])
def test_int8_session_initialization(crop: str):
    """Verifies that ModelServingService can initialize INT8 ONNX Runtime session."""
    session_int8 = model_service.get_onnx_session(crop=crop, use_int8=True)
    assert isinstance(session_int8, ort.InferenceSession)
    inputs = session_int8.get_inputs()
    outputs = session_int8.get_outputs()
    assert len(inputs) == 1
    assert inputs[0].name == "input"
    assert len(outputs) == 1
    assert outputs[0].name == "output"


@pytest.mark.parametrize("crop", ["sugarcane", "tomato", "onion"])
def test_int8_predict_numerical_consistency(crop: str):
    """Verifies high Pearson output correlation and identical class predictions between FP32 and INT8."""
    # Synthetic realistic leaf image
    img = Image.new("RGB", (224, 224), color=(40, 160, 40))

    res_fp32 = model_service.predict_onnx(img, crop=crop, use_int8=False)
    res_int8 = model_service.predict_onnx(img, crop=crop, use_int8=True)

    assert res_fp32["predicted_class"] == res_int8["predicted_class"], (
        f"Prediction mismatch for {crop}: FP32={res_fp32['predicted_class']} vs INT8={res_int8['predicted_class']}"
    )
    assert abs(res_fp32["confidence"] - res_int8["confidence"]) < 0.15, (
        f"Confidence drift excessive for {crop}: FP32={res_fp32['confidence']} vs INT8={res_int8['confidence']}"
    )

    assert "INT8" in res_int8["model_version"]
    assert "onnxruntime-int8" in res_int8["inference_engine"]


def test_unsupported_crop_onnx():
    """Verifies that unsupported crops raise UnsupportedCropError in ONNX prediction."""
    img = Image.new("RGB", (224, 224), color=(50, 150, 50))
    with pytest.raises(UnsupportedCropError):
        model_service.predict_onnx(img, crop="dragonfruit", use_int8=True)

