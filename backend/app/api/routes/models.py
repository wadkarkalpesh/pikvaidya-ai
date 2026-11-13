"""
PikVaidya AI — Model Registry & Architecture Metadata API
=========================================================
Exposes transparent technical specifications for all deployed computer vision models,
including input dimensions, class vocabularies, quantization status, and benchmark metrics.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from app.services.model_service import model_service

router = APIRouter()

MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
    "crop_gate": {
        "model_id": "crop_gate_mobilenetv3_small",
        "name": "Hierarchical Crop Classifier Gate",
        "crop": "universal",
        "architecture": "MobileNetV3-Small",
        "input_dimensions": [3, 224, 224],
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "num_classes": 3,
        "classes": ["sugarcane", "tomato", "onion"],
        "checkpoint_path": "models/crop_detector.pth",
        "quantized_onnx_path": None,
        "test_accuracy": 0.9967,
        "macro_f1": 0.9965,
        "parameters": "1.52M",
        "status": "PRODUCTION_ACTIVE",
        "role": "Stage-1 hierarchical routing gate preventing inter-crop feature interference."
    },
    "sugarcane": {
        "model_id": "sugarcane_mobilenetv3_large",
        "name": "Sugarcane Foliar Pathology Specialist",
        "crop": "sugarcane",
        "architecture": "MobileNetV3-Large",
        "input_dimensions": [3, 224, 224],
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "num_classes": 5,
        "classes": ["Healthy", "Mosaic", "RedRot", "Rust", "Yellow"],
        "checkpoint_path": "models/sugarcane_model.pth",
        "quantized_onnx_path": "models/sugarcane_mobilenetv3_int8.onnx",
        "test_accuracy": 0.9840,
        "macro_f1": 0.9835,
        "quantized_size_mb": 11.86,
        "parameters": "4.21M",
        "status": "PRODUCTION_ACTIVE",
        "gradcam_target_layer": "features[16]",
        "calibration": "Platt Softmax Temperature Scaling (tau=1.25)",
        "role": "Dedicated diagnostic specialist for Western Maharashtra sugarcane cash-crops."
    },
    "tomato": {
        "model_id": "tomato_mobilenetv3_large",
        "name": "Tomato Foliar Pathology Specialist",
        "crop": "tomato",
        "architecture": "MobileNetV3-Large",
        "input_dimensions": [3, 224, 224],
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "num_classes": 10,
        "classes": [
            "Bacterial_spot", "Early_blight", "Late_blight", "Leaf_Mold",
            "Septoria_leaf_spot", "Spider_mites", "Target_Spot",
            "Yellow_Leaf_Curl_Virus", "Mosaic_virus", "Healthy"
        ],
        "checkpoint_path": "models/tomato_model.pth",
        "quantized_onnx_path": "models/tomato_mobilenetv3_int8.onnx",
        "test_accuracy": 0.9910,
        "macro_f1": 0.9908,
        "quantized_size_mb": 11.86,
        "parameters": "4.21M",
        "status": "PRODUCTION_ACTIVE",
        "gradcam_target_layer": "features[16]",
        "calibration": "Platt Softmax Temperature Scaling (tau=1.25)",
        "role": "High-precision 10-class diagnostic specialist for solanaceous tomato crops."
    },
    "onion": {
        "model_id": "onion_mobilenetv3_large",
        "name": "Onion Foliar Pathology Specialist",
        "crop": "onion",
        "architecture": "MobileNetV3-Large",
        "input_dimensions": [3, 224, 224],
        "normalization": {
            "mean": [0.485, 0.456, 0.406],
            "std": [0.229, 0.224, 0.225],
        },
        "num_classes": 4,
        "classes": ["Healthy", "Purple_Blotch", "Stemphylium_Leaf_Blight", "Iris_Yellow_Spot_Virus"],
        "checkpoint_path": "models/onion_model.pth",
        "quantized_onnx_path": "models/onion_mobilenetv3_large_int8.onnx",
        "test_accuracy": 0.9862,
        "macro_f1": 0.9885,
        "quantized_size_mb": 11.86,
        "parameters": "4.21M",
        "status": "PRODUCTION_ACTIVE",
        "gradcam_target_layer": "features[16]",
        "calibration": "Platt Softmax Temperature Scaling (tau=1.25)",
        "role": "Targeted pathology model for rabi and kharif onion cultivation."
    },
    "cotton": {
        "model_id": "cotton_model_phase2",
        "name": "Cotton Pathology Model (Planned)",
        "crop": "cotton",
        "status": "PLANNED_PHASE_2",
        "notes": "Dataset curation and multi-center field validation scheduled for Phase 2."
    },
    "soybean": {
        "model_id": "soybean_model_phase2",
        "name": "Soybean Pathology Model (Planned)",
        "crop": "soybean",
        "status": "PLANNED_PHASE_2",
        "notes": "Dataset curation and multi-center field validation scheduled for Phase 2."
    }
}


@router.get("", response_model=Dict[str, Any], summary="List all deployed crop disease models")
def list_models():
    """Returns detailed technical metadata for all active and planned neural network models."""
    active_crops = [k for k, v in MODEL_CATALOG.items() if v.get("status") == "PRODUCTION_ACTIVE"]
    return {
        "active_models_count": len(active_crops),
        "supported_crops": ["sugarcane", "tomato", "onion"],
        "planned_crops": ["cotton", "soybean"],
        "models": MODEL_CATALOG
    }


@router.get("/{crop}", response_model=Dict[str, Any], summary="Get metadata for a specific crop model")
def get_model_by_crop(crop: str):
    """Fetches architecture, class names, checkpoint path, and benchmark metrics for a specific crop."""
    norm_crop = crop.strip().lower()
    if norm_crop not in MODEL_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model for crop '{crop}' not found. Supported crops: {list(MODEL_CATALOG.keys())}"
        )
    return MODEL_CATALOG[norm_crop]
