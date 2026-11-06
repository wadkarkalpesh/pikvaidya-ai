"""
PikVaidya AI — Neural Network ONNX Export & Edge Optimization Pipeline
======================================================================
Converts PyTorch model checkpoints (Sugarcane & Tomato) into optimized ONNX
format with dynamic batching, numerical parity verification, and latency benchmarking.
"""

import os
import sys
import time
from pathlib import Path

# Ensure non-production environment defaults for standalone script execution
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "export-onnx-development-key-32-characters"

import torch
import torch.nn as nn
from torchvision import models
import numpy as np
import onnx
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.model_service import model_service

MODELS_TO_EXPORT = [
    {
        "crop": "sugarcane",
        "arch": "efficientnet_b0",
        "num_classes": 5,
        "checkpoint": PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "pipeline_trained" / "best_model.pth",
        "output_onnx": PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "model.onnx",
    },
    {
        "crop": "sugarcane",
        "arch": "mobilenet_v3",
        "num_classes": 5,
        "checkpoint": PROJECT_ROOT / "models" / "sugarcane" / "mobilenet_v3" / "pipeline_trained" / "best_model.pth",
        "output_onnx": PROJECT_ROOT / "models" / "sugarcane" / "mobilenet_v3" / "model.onnx",
    },
    {
        "crop": "tomato",
        "arch": "mobilenet_v3",
        "num_classes": 10,
        "checkpoint": PROJECT_ROOT / "models" / "tomato" / "mobilenet_v3" / "best_model.pth",
        "output_onnx": PROJECT_ROOT / "models" / "tomato" / "mobilenet_v3" / "model.onnx",
    },
]


def export_and_verify(config: dict):
    crop = config["crop"]
    arch = config["arch"]
    num_classes = config["num_classes"]
    ckpt_path = config["checkpoint"]
    onnx_path = config["output_onnx"]

    print(f"\n=================================================================")
    print(f"Exporting: {crop.upper()} ({arch}) -> {onnx_path.name}")
    print(f"Checkpoint: {ckpt_path}")
    print(f"=================================================================")

    if not ckpt_path.exists():
        print(f"ERROR: Checkpoint not found at {ckpt_path}")
        return False

    model = model_service._build_architecture(arch_type=arch, num_classes=num_classes)
    checkpoint = torch.load(ckpt_path, map_location="cpu")
    state_dict = checkpoint["state_dict"] if "state_dict" in checkpoint else checkpoint
    
    # Filter out any non-weight attributes like target_conv_layer if present
    filtered_state = {k: v for k, v in state_dict.items() if not k.startswith("target_conv_layer")}
    model.load_state_dict(filtered_state, strict=False)
    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224, requires_grad=False)

    # 1. Export to ONNX
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        },
    )

    # 2. Check ONNX Model Structure
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    file_size_mb = onnx_path.stat().st_size / (1024 * 1024)
    print(f"✓ ONNX export valid! Model size: {file_size_mb:.2f} MB")

    # 3. Numerical Parity Verification (PyTorch vs ONNX Runtime)
    with torch.no_grad():
        torch_out = model(dummy_input).numpy()

    ort_session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_inputs = {"input": dummy_input.numpy()}
    ort_out = ort_session.run(None, ort_inputs)[0]

    max_abs_diff = float(np.max(np.abs(torch_out - ort_out)))
    cosine_sim = float(
        np.dot(torch_out.flatten(), ort_out.flatten())
        / (np.linalg.norm(torch_out) * np.linalg.norm(ort_out))
    )
    class_match = bool(np.argmax(torch_out) == np.argmax(ort_out))

    print(f"✓ Numerical parity check:")
    print(f"    - Max absolute logit diff: {max_abs_diff:.6f}")
    print(f"    - Cosine logit similarity: {cosine_sim:.6f}")
    print(f"    - Argmax predicted class match: {class_match}")
    assert cosine_sim > 0.999, f"Cosine similarity too low: {cosine_sim}"
    assert class_match, "Predicted classes diverged between PyTorch and ONNX!"

    # 4. Latency Benchmark (50 iterations)
    warmup = 10
    runs = 50

    # PyTorch latency
    for _ in range(warmup):
        with torch.no_grad():
            _ = model(dummy_input)
    t0 = time.perf_counter()
    for _ in range(runs):
        with torch.no_grad():
            _ = model(dummy_input)
    torch_latency_ms = ((time.perf_counter() - t0) / runs) * 1000

    # ONNX Runtime latency
    for _ in range(warmup):
        _ = ort_session.run(None, ort_inputs)
    t0 = time.perf_counter()
    for _ in range(runs):
        _ = ort_session.run(None, ort_inputs)
    ort_latency_ms = ((time.perf_counter() - t0) / runs) * 1000

    speedup = torch_latency_ms / max(ort_latency_ms, 1e-6)
    print(f"✓ PyTorch CPU Latency:  {torch_latency_ms:.2f} ms")
    print(f"✓ ONNXRuntime Latency:  {ort_latency_ms:.2f} ms ({speedup:.2f}x speedup)")

    return True


if __name__ == "__main__":
    success_count = 0
    for cfg in MODELS_TO_EXPORT:
        if export_and_verify(cfg):
            success_count += 1
    print(f"\n=================================================================")
    print(f"SUMMARY: Successfully exported & verified {success_count}/{len(MODELS_TO_EXPORT)} models to ONNX!")
    print(f"=================================================================")
