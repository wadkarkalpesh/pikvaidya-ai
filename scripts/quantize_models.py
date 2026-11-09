"""
PikVaidya AI — Edge Model Dynamic INT8 Quantization Pipeline
============================================================
Quantizes FP32 ONNX neural network models for Sugarcane, Tomato, and Onion
to INT8 using dynamic quantization with per-channel weight scaling.

Features:
1. Sanitizes ONNX value_info against initializer collisions
2. Quantizes linear projection / classifier layers (MatMul / Gemm) to signed 8-bit integers
3. Rigorous numerical parity verification (Pearson correlation > 0.99)
4. CPU inference latency benchmarking (50 iterations)
5. Generates edge-optimized model_int8.onnx checkpoints
"""

import os
import sys
import time
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODELS = [
    {
        "crop": "sugarcane",
        "arch": "efficientnet_b0",
        "fp32_path": PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "model.onnx",
        "int8_path": PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "model_int8.onnx",
    },
    {
        "crop": "sugarcane",
        "arch": "mobilenet_v3",
        "fp32_path": PROJECT_ROOT / "models" / "sugarcane" / "mobilenet_v3" / "model.onnx",
        "int8_path": PROJECT_ROOT / "models" / "sugarcane" / "mobilenet_v3" / "model_int8.onnx",
    },
    {
        "crop": "tomato",
        "arch": "mobilenet_v3",
        "fp32_path": PROJECT_ROOT / "models" / "tomato" / "mobilenet_v3" / "model.onnx",
        "int8_path": PROJECT_ROOT / "models" / "tomato" / "mobilenet_v3" / "model_int8.onnx",
    },
    {
        "crop": "onion",
        "arch": "mobilenet_v3",
        "fp32_path": PROJECT_ROOT / "models" / "onion" / "mobilenet_v3" / "model.onnx",
        "int8_path": PROJECT_ROOT / "models" / "onion" / "mobilenet_v3" / "model_int8.onnx",
    },
]


def sanitize_onnx_model(model_proto: onnx.ModelProto) -> onnx.ModelProto:
    """Removes value_info entries that collide with initializers to avoid onnxruntime shape inference bug."""
    init_names = {init.name for init in model_proto.graph.initializer}
    val_infos = [vi for vi in model_proto.graph.value_info if vi.name not in init_names]
    model_proto.graph.ClearField("value_info")
    model_proto.graph.value_info.extend(val_infos)
    return model_proto


def quantize_and_benchmark(model_cfg: dict):
    crop = model_cfg["crop"]
    arch = model_cfg["arch"]
    fp32_path = model_cfg["fp32_path"]
    int8_path = model_cfg["int8_path"]

    print("\n" + "=" * 70)
    print(f"QUANTIZING: {crop.upper()} ({arch})")
    print(f"Source FP32: {fp32_path}")
    print(f"Target INT8: {int8_path}")
    print("=" * 70)

    if not fp32_path.exists():
        print(f"ERROR: FP32 model not found at {fp32_path}")
        return False

    # 1. Load and sanitize model
    model = onnx.load(str(fp32_path))
    model = sanitize_onnx_model(model)
    
    # Save sanitized temporary version if needed
    temp_sanitized = fp32_path.with_name("temp_sanitized.onnx")
    onnx.save(model, str(temp_sanitized))

    # 2. Dynamic INT8 Quantization
    quantize_dynamic(
        model_input=str(temp_sanitized),
        model_output=str(int8_path),
        op_types_to_quantize=["MatMul", "Gemm"],
        weight_type=QuantType.QInt8,
        per_channel=True,
    )

    if temp_sanitized.exists():
        temp_sanitized.unlink()

    # 3. Model Size Comparison
    size_fp32 = os.path.getsize(str(fp32_path))
    size_int8 = os.path.getsize(str(int8_path))
    reduction_pct = (1.0 - (size_int8 / size_fp32)) * 100.0

    print(f"FP32 Size: {size_fp32:,} bytes ({size_fp32 / (1024*1024):.2f} MB)")
    print(f"INT8 Size: {size_int8:,} bytes ({size_int8 / (1024*1024):.2f} MB)")
    print(f"Size Reduction: {reduction_pct:.2f}% (Savings: {(size_fp32 - size_int8) / 1024:.1f} KB)")

    # 4. Numerical Parity & Output Correlation Check
    session_fp32 = ort.InferenceSession(str(fp32_path), providers=["CPUExecutionProvider"])
    session_int8 = ort.InferenceSession(str(int8_path), providers=["CPUExecutionProvider"])

    np.random.seed(42)
    dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)

    out_fp32 = session_fp32.run(None, {"input": dummy_input})[0]
    out_int8 = session_int8.run(None, {"input": dummy_input})[0]

    max_abs_diff = float(np.max(np.abs(out_fp32 - out_int8)))
    corr = float(np.corrcoef(out_fp32.flatten(), out_int8.flatten())[0, 1])

    print(f"Max Absolute Logit Difference: {max_abs_diff:.6f}")
    print(f"Pearson Output Correlation:    {corr:.6f}")
    assert corr > 0.99, f"Quantization drift warning: correlation {corr:.4f} is below 0.99 threshold!"

    # 5. Latency Benchmarking (50 warmup + 50 timed iterations)
    for _ in range(20):
        _ = session_fp32.run(None, {"input": dummy_input})
        _ = session_int8.run(None, {"input": dummy_input})

    iters = 50
    t0 = time.perf_counter()
    for _ in range(iters):
        _ = session_fp32.run(None, {"input": dummy_input})
    lat_fp32 = (time.perf_counter() - t0) * 1000.0 / iters

    t0 = time.perf_counter()
    for _ in range(iters):
        _ = session_int8.run(None, {"input": dummy_input})
    lat_int8 = (time.perf_counter() - t0) * 1000.0 / iters

    print(f"FP32 Inference Latency: {lat_fp32:.2f} ms/sample")
    print(f"INT8 Inference Latency: {lat_int8:.2f} ms/sample")
    print(f"Status: VERIFIED & OPTIMIZED FOR EDGE DEPLOYMENT")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("PIKVAIDYA AI: NEURAL NETWORK INT8 DYNAMIC QUANTIZATION")
    print("=" * 70)
    all_success = True
    for cfg in MODELS:
        ok = quantize_and_benchmark(cfg)
        if not ok:
            all_success = False

    if all_success:
        print("\nALL MODELS QUANTIZED AND VALIDATED SUCCESSFULLY!")
    else:
        print("\nSOME MODELS ENCOUNTERED ISSUES.")
        sys.exit(1)

