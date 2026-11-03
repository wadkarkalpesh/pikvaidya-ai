#!/usr/bin/env python3
"""
PikVaidya AI — Grad-CAM Explainability Test Suite
=================================================
Automated verification of:
  - Checkpoint integrity & SHA-256 immutability
  - Target convolutional layer selection (features[-1])
  - Hook registration, lifecycle, and memory leak cleanup
  - Grad-CAM heatmap dimensionality, range [0, 1], and finite values
  - Zero inference interference (model weights untouched, logits identical)
  - Colormap rendering, bilinear resizing, and overlay blending
"""

import sys
import hashlib
from pathlib import Path
import pytest
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training.models import build_model
from src.data.dataset import get_transforms
from src.explainability.gradcam import GradCAM
from src.explainability.visualization import (
    jet_colormap,
    apply_colormap_on_image,
    create_explanation_summary,
)

EXPECTED_SHA256 = "3881BE5975C29D14C0969932B70562391BB614190FCEC9CF9F8EFB41AAE670C4"


@pytest.fixture(scope="module")
def checkpoint_path() -> Path:
    """Fixture resolving existing best_model.pth checkpoint."""
    p = PROJECT_ROOT / "checkpoints" / "best_model.pth"
    if not p.exists():
        p = PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "best_model.pth"
    assert p.exists(), f"Model checkpoint not found at {p}"
    return p


@pytest.fixture(scope="module")
def loaded_model(checkpoint_path: Path) -> nn.Module:
    """Fixture returning loaded EfficientNet-B0 model."""
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    model = build_model("efficientnet_b0", num_classes=5, pretrained=False)
    state_dict = ckpt.get("state_dict", ckpt)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def test_checkpoint_immutability(checkpoint_path: Path):
    """Verifies checkpoint file exists and its SHA-256 hash matches the baseline exactly."""
    hasher = hashlib.sha256()
    with open(checkpoint_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    file_hash = hasher.hexdigest().upper()
    assert file_hash == EXPECTED_SHA256, (
        f"Checkpoint hash mismatch! Expected {EXPECTED_SHA256}, got {file_hash}. "
        "Model checkpoint must never be modified or overwritten."
    )


def test_target_conv_layer_architecture(loaded_model: nn.Module):
    """Verifies EfficientNet-B0 has target_conv_layer pointing to features[-1]."""
    assert hasattr(loaded_model, "features"), "Model must have 'features' module."
    last_block = loaded_model.features[-1]
    assert hasattr(loaded_model, "target_conv_layer"), "Model must expose target_conv_layer."
    assert loaded_model.target_conv_layer is last_block, "target_conv_layer must be model.features[-1]."

    # Test forward pass through feature extractor
    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        feat = loaded_model.features(dummy_input)
    assert feat.shape == (1, 1280, 7, 7), f"Expected feature map (1, 1280, 7, 7), got {feat.shape}"


def test_gradcam_hook_lifecycle(loaded_model: nn.Module):
    """Verifies hooks are attached upon initialization and cleanly removed upon teardown."""
    gc = GradCAM(loaded_model)
    assert gc.f_handle is not None, "Forward hook handle must be active."
    assert gc.b_handle is not None, "Backward hook handle must be active."

    # Manually remove hooks
    gc.remove_hooks()
    assert gc.f_handle is None, "Forward hook handle must be None after remove_hooks()."
    assert gc.b_handle is None, "Backward hook handle must be None after remove_hooks()."

    # Context manager lifecycle
    with GradCAM(loaded_model) as gc_ctx:
        assert gc_ctx.f_handle is not None
        assert gc_ctx.b_handle is not None
    assert gc_ctx.f_handle is None
    assert gc_ctx.b_handle is None


def test_gradcam_heatmap_properties(loaded_model: nn.Module):
    """Verifies Grad-CAM heatmap dimensionality, range [0, 1], and finite values."""
    with GradCAM(loaded_model) as gc:
        dummy_input = torch.randn(1, 3, 224, 224)
        
        # Test default mode (returns 2D numpy array)
        cam_default = gc.generate_cam(dummy_input)
        assert cam_default.shape == (7, 7), f"Expected default CAM shape (7, 7), got {cam_default.shape}"
        assert isinstance(cam_default, np.ndarray), "CAM output must be a numpy ndarray."

        # Test detailed mode (returns tuple with metadata)
        cam, pred_class, conf, probs = gc.generate_cam(dummy_input, return_details=True)

        # Output shape should match target conv layer spatial dimensions (7, 7)
        assert cam.shape == (7, 7), f"Expected CAM shape (7, 7), got {cam.shape}"
        assert isinstance(cam, np.ndarray), "CAM output must be a numpy ndarray."

        # Value bounds and finiteness
        assert np.all(np.isfinite(cam)), "CAM mask must contain only finite numbers (no NaN or Inf)."
        assert float(cam.min()) >= 0.0 - 1e-6, f"CAM minimum value {cam.min()} must be >= 0."
        assert float(cam.max()) <= 1.0 + 1e-6, f"CAM maximum value {cam.max()} must be <= 1."

        # Softmax probability sanity
        assert 0 <= pred_class < 5, f"Predicted class {pred_class} out of range [0, 4]."
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} must be in [0, 1]."
        assert torch.isclose(torch.sum(probs), torch.tensor(1.0), atol=1e-4), "Softmax probs must sum to 1.0."


def test_target_class_selection(loaded_model: nn.Module):
    """Verifies Grad-CAM responds distinctly when evaluating different target classes."""
    with GradCAM(loaded_model) as gc:
        dummy_input = torch.randn(1, 3, 224, 224)

        # Class 0 vs Class 2
        cam_c0 = gc.generate_cam(dummy_input, target_class=0)
        cam_c2 = gc.generate_cam(dummy_input, target_class=2)

        assert cam_c0.shape == (7, 7)
        assert cam_c2.shape == (7, 7)
        # Activation maps for contrasting classes should not be identical
        assert not np.allclose(cam_c0, cam_c2, atol=1e-5), "CAM maps for contrasting classes should differ."


def test_zero_inference_interference(loaded_model: nn.Module):
    """Verifies that computing Grad-CAM does not mutate model weights or alter subsequent predictions."""
    test_tensor = torch.randn(1, 3, 224, 224)

    # 1. Capture predictions before Grad-CAM
    with torch.no_grad():
        logits_before = loaded_model(test_tensor).clone()
        weights_before = [p.clone() for p in loaded_model.parameters()]

    # 2. Run Grad-CAM
    with GradCAM(loaded_model) as gc:
        _ = gc.generate_cam(test_tensor)

    # 3. Capture predictions after Grad-CAM
    with torch.no_grad():
        logits_after = loaded_model(test_tensor).clone()
        weights_after = [p.clone() for p in loaded_model.parameters()]

    # Assert model weights remained identical
    for idx, (w_b, w_a) in enumerate(zip(weights_before, weights_after)):
        assert torch.equal(w_b, w_a), f"Parameter tensor {idx} was modified during Grad-CAM!"

    # Assert inference output remained identical
    assert torch.allclose(logits_before, logits_after, atol=1e-6), (
        "Model logits changed after running Grad-CAM! Forward pass must remain pristine."
    )


def test_visualization_pipeline(tmp_path: Path):
    """Verifies JET colormap generation, resizing, overlay blending, and 4-panel diagnostic card."""
    dummy_img = Image.new("RGB", (300, 400), color=(100, 150, 200))
    dummy_cam = np.random.uniform(0.0, 1.0, size=(7, 7)).astype(np.float32)

    # Jet colormap direct test
    jet_arr = jet_colormap(dummy_cam)
    assert jet_arr.shape == (7, 7, 3), f"Expected (7, 7, 3), got {jet_arr.shape}"
    assert jet_arr.dtype == np.uint8, "Expected uint8 array"

    # Apply colormap on image (standalone overlay)
    single_overlay = apply_colormap_on_image(dummy_img, dummy_cam, alpha=0.5)
    assert single_overlay.size == (300, 400), f"Overlay size {single_overlay.size} must match original (300, 400)"

    # Apply colormap on image (pair mode)
    heatmap_img, overlay_img = apply_colormap_on_image(dummy_img, dummy_cam, alpha=0.5, return_pair=True)
    assert heatmap_img.size == (300, 400), f"Heatmap size {heatmap_img.size} must match original (300, 400)"
    assert overlay_img.size == (300, 400), f"Overlay size {overlay_img.size} must match original (300, 400)"

    # Create 4-panel explanation summary
    summary_path = tmp_path / "test_summary.png"
    pred_info = {
        "actual_class": "RedRot",
        "predicted_class": "RedRot",
        "confidence": 0.9542,
        "correct": True,
        "device": "CPU",
        "target_layer": "features[-1]",
        "class_scores": {"Healthy": 0.01, "Mosaic": 0.01, "RedRot": 0.95, "Rust": 0.02, "Yellow": 0.01}
    }
    composite = create_explanation_summary(
        dummy_img, heatmap_img, overlay_img, pred_info, output_path=summary_path
    )
    assert summary_path.exists(), "Summary report image must be written to disk."
    assert composite.size[0] > 1000, "Composite width should accommodate 4 panels."
