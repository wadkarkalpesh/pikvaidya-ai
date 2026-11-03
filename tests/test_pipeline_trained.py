#!/usr/bin/env python3
"""
PikVaidya AI — Pipeline Trained Model & Explainability Verification Test
========================================================================
Automated validation of:
  - Pipeline trained checkpoint existence and format
  - Classification head architecture and class count (5)
  - Validation Macro-F1 threshold compliance
  - Grad-CAM saliency generation on newly trained weights
  - Target conv layer hooks and memory cleanup
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training.models import build_model
from src.data.dataset import get_transforms
from src.explainability.gradcam import GradCAM
from src.explainability.visualization import apply_colormap_on_image

PIPELINE_CHECKPOINT = PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "pipeline_trained" / "best_model.pth"


@pytest.mark.skipif(not PIPELINE_CHECKPOINT.exists(), reason="Pipeline trained checkpoint not generated yet.")
def test_pipeline_checkpoint_structure():
    """Verifies newly trained checkpoint contains required keys and valid weights."""
    ckpt = torch.load(PIPELINE_CHECKPOINT, map_location="cpu")
    required_keys = ["epoch", "model_name", "state_dict", "optimizer_state_dict", "val_macro_f1", "val_accuracy", "class_to_idx", "idx_to_class"]
    for k in required_keys:
        assert k in ckpt, f"Key '{k}' missing from pipeline checkpoint!"

    assert ckpt["val_macro_f1"] > 0.70, f"Validation Macro-F1 {ckpt['val_macro_f1']} is below minimum threshold."
    assert len(ckpt["class_to_idx"]) == 5, "Class mapping must contain 5 classes."


@pytest.mark.skipif(not PIPELINE_CHECKPOINT.exists(), reason="Pipeline trained checkpoint not generated yet.")
def test_pipeline_model_inference():
    """Verifies forward pass through newly trained EfficientNet-B0 model."""
    ckpt = torch.load(PIPELINE_CHECKPOINT, map_location="cpu")
    model = build_model("efficientnet_b0", num_classes=5, pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    dummy_input = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        logits = model(dummy_input)
        probs = torch.softmax(logits, dim=1)

    assert logits.shape == (2, 5), f"Expected logits shape (2, 5), got {logits.shape}"
    assert torch.allclose(torch.sum(probs, dim=1), torch.ones(2), atol=1e-4), "Softmax probabilities must sum to 1.0"


@pytest.mark.skipif(not PIPELINE_CHECKPOINT.exists(), reason="Pipeline trained checkpoint not generated yet.")
def test_pipeline_model_gradcam():
    """Verifies Grad-CAM generation using newly trained model weights."""
    ckpt = torch.load(PIPELINE_CHECKPOINT, map_location="cpu")
    model = build_model("efficientnet_b0", num_classes=5, pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    with GradCAM(model, model.features[-1]) as gc:
        dummy_input = torch.randn(1, 3, 224, 224)
        cam_mask, pred_cls, conf, probs = gc.generate_cam(dummy_input, return_details=True)

        assert cam_mask.shape == (7, 7)
        assert np.all(np.isfinite(cam_mask))
        assert 0.0 <= cam_mask.min() and cam_mask.max() <= 1.0
        assert 0 <= pred_cls < 5

