#!/usr/bin/env python3
"""
PikVaidya AI — Explainable AI (Grad-CAM) Visual Explanations
===========================================================
Generates Gradient-weighted Class Activation Maps (Grad-CAM) for vision backbones:
 - EfficientNet-B0 (last conv feature map)
 - MobileNetV3 (last conv feature map)
 - ResNet-50 (layer4 residual block)
Overlays visual heatmaps to verify lesion localization for Indian farmers.
"""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T


class GradCAM:
    """Hooks into target convolutional layer to compute class activation maps."""
    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model.eval()
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        
        # Register forward and backward hooks
        self.target_layer.register_forward_hook(self._forward_hook)
        self.target_layer.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, module, input, output):
        self.activations = output.detach()

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_cam(self, input_tensor: torch.Tensor, target_class: Optional[int] = None) -> np.ndarray:
        """Computes normalized Grad-CAM heatmap for the input tensor."""
        self.model.zero_grad()
        output = self.model(input_tensor)

        if target_class is None:
            target_class = torch.argmax(output, dim=1).item()

        score = output[0, target_class]
        score.backward()

        # Global average pooling of gradients: alpha_k
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)
        # Weighted combination of forward activation maps
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
        # Apply ReLU to focus only on features with a positive influence on the target class
        cam = torch.clamp(cam, min=0)

        cam = cam.squeeze().cpu().numpy()
        # Normalize to [0, 1]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max > cam_min:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        return cam


def apply_colormap_on_image(
    original_img: Image.Image,
    cam_mask: np.ndarray,
    output_path: Optional[Path] = None,
    alpha: float = 0.5
) -> Image.Image:
    """Resizes CAM mask, converts to RGB heatmap, and overlays onto the original PIL image."""
    orig_w, orig_h = original_img.size
    # Resize CAM to match original image dimensions using PIL
    mask_img = Image.fromarray((cam_mask * 255).astype(np.uint8)).resize((orig_w, orig_h), Image.Resampling.BILINEAR)
    mask_arr = np.array(mask_img, dtype=float) / 255.0

    # Synthetic JET colormap in pure NumPy
    # Red for high activation, Yellow for mid, Blue for low
    r = np.clip(1.5 - np.abs(2.0 * mask_arr - 1.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(2.0 * mask_arr - 0.5), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(2.0 * mask_arr - 0.0), 0.0, 1.0)
    heatmap = np.stack([r, g, b], axis=-1) * 255.0

    orig_arr = np.array(original_img.convert("RGB"), dtype=float)
    blended = (1.0 - alpha) * orig_arr + alpha * heatmap
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    blended_img = Image.fromarray(blended)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        blended_img.save(output_path)

    return blended_img
