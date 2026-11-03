#!/usr/bin/env python3
"""
PikVaidya AI — Explainable AI (Grad-CAM) Core Engine
===================================================
Implementation of Gradient-weighted Class Activation Mapping (Grad-CAM)
for deep convolutional architectures in agricultural pathology diagnosis:
  - EfficientNet-B0 (target: final conv stage 'features[-1]')
  - MobileNetV3-Large (target: final conv stage 'features[-1]')
  - ResNet-50 (target: residual block 'layer4[-1]')

Formulation:
  alpha_k^c = (1 / Z) * sum_i sum_j (d Y^c / d A_{i,j}^k)
  L_{Grad-CAM}^c = ReLU( sum_k alpha_k^c * A^k )

Features:
  - Supports both predicted-class and user-specified target-class saliency
  - Compatible with CUDA GPU acceleration and CPU fallback
  - Memory-leak prevention with explicit hook registration handles & context manager
  - Numerical stability checks (finite values, min-max normalization in [0, 1])
  - Non-destructive execution: leaves underlying model weights untouched
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
from PIL import Image

# Re-export visualization helper for backward compatibility
from src.explainability.visualization import apply_colormap_on_image


class GradCAM:
    """
    Computes Gradient-weighted Class Activation Mapping (Grad-CAM) heatmaps
    by hooking into intermediate convolutional feature layers.
    """

    def __init__(self, model: nn.Module, target_layer: Optional[nn.Module] = None):
        """
        Initializes GradCAM with model and target convolutional layer.
        
        Args:
            model: PyTorch classification model (e.g. EfficientNet-B0).
            target_layer: Target nn.Module layer. If None, automatically detects
                          target_conv_layer attribute or falls back to model.features[-1].
        """
        self.model = model
        self.model.eval()

        # Identify target convolutional layer
        if target_layer is not None:
            self.target_layer = target_layer
        elif hasattr(model, "target_conv_layer") and model.target_conv_layer is not None:
            self.target_layer = model.target_conv_layer
        elif hasattr(model, "features"):
            self.target_layer = model.features[-1]
        elif hasattr(model, "layer4"):
            self.target_layer = model.layer4[-1]
        else:
            raise ValueError(
                "Could not automatically detect target convolutional layer. "
                "Please explicitly specify 'target_layer'."
            )

        self.target_layer_name = self._resolve_layer_name(model, self.target_layer)
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None

        # Register forward and backward hooks with tracking handles
        self.f_handle = self.target_layer.register_forward_hook(self._forward_hook)
        self.b_handle = self.target_layer.register_full_backward_hook(self._backward_hook)

    @staticmethod
    def _resolve_layer_name(model: nn.Module, target_layer: nn.Module) -> str:
        """Finds the string attribute path of the target layer within the model."""
        for name, module in model.named_modules():
            if module is target_layer:
                return name
        return "target_conv_layer"

    def _forward_hook(self, module: nn.Module, input: Tuple[torch.Tensor, ...], output: torch.Tensor):
        """Forward hook capturing feature map activations."""
        self.activations = output.detach()

    def _backward_hook(self, module: nn.Module, grad_input: Tuple[torch.Tensor, ...], grad_output: Tuple[torch.Tensor, ...]):
        """Backward hook capturing gradients flowing back from target class score."""
        self.gradients = grad_output[0].detach()

    def remove_hooks(self):
        """Removes registered PyTorch hooks to avoid memory leaks and overhead."""
        if hasattr(self, "f_handle") and self.f_handle is not None:
            self.f_handle.remove()
            self.f_handle = None
        if hasattr(self, "b_handle") and self.b_handle is not None:
            self.b_handle.remove()
            self.b_handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_hooks()

    def generate_cam(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None,
        return_details: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, int, float, torch.Tensor]]:
        """
        Generates normalized Grad-CAM heatmap for a single input image tensor.

        Args:
            input_tensor: 4D tensor (1, C, H, W) or 3D tensor (C, H, W).
            target_class: Integer index of target class. If None, uses argmax(logits).
            return_details: If False (default), returns normalized 2D numpy array cam_mask.
                            If True, returns tuple (cam_mask, pred_class, pred_conf, probs).

        Returns:
            cam_mask OR (cam_mask, pred_class, pred_conf, probs)
        """
        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)

        device = next(self.model.parameters()).device
        input_tensor = input_tensor.to(device)

        # Clear existing gradients
        self.model.zero_grad()
        self.activations = None
        self.gradients = None

        # Execute forward pass with gradients enabled
        with torch.enable_grad():
            input_tensor.requires_grad_(True)
            logits = self.model(input_tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0)
            pred_class = int(torch.argmax(logits, dim=1).item())
            pred_conf = float(probs[pred_class].item())

            # Select target class score
            selected_class = pred_class if target_class is None else int(target_class)
            score = logits[0, selected_class]

            # Backward pass to obtain gradients at target layer
            score.backward(retain_graph=False)

        if self.activations is None or self.gradients is None:
            raise RuntimeError(
                f"Failed to capture activations or gradients at target layer '{self.target_layer_name}'. "
                "Ensure target layer is exercised during the forward and backward passes."
            )

        # Global average pooling of gradients: alpha_k = (1/Z) * sum_i sum_j (d Y^c / d A_{i,j}^k)
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)  # Shape: (1, C, 1, 1)

        # Weighted combination of forward activation maps: sum_k alpha_k * A^k
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)  # Shape: (1, 1, H, W)

        # Apply ReLU to retain only positive influences on target score
        cam = torch.clamp(cam, min=0.0)

        # Convert to numpy
        cam_np = cam.squeeze().cpu().numpy()

        # Handle zero-variance / non-finite values safely
        if not np.all(np.isfinite(cam_np)):
            cam_np = np.nan_to_num(cam_np, nan=0.0, posinf=1.0, neginf=0.0)

        cam_min, cam_max = float(cam_np.min()), float(cam_np.max())
        if cam_max > cam_min:
            cam_norm = (cam_np - cam_min) / (cam_max - cam_min)
        else:
            cam_norm = np.zeros_like(cam_np, dtype=np.float32)

        # Memory cleanup
        self.model.zero_grad()
        if input_tensor.grad is not None:
            input_tensor.grad.detach_()
            input_tensor.grad.zero_()

        if return_details:
            return cam_norm, pred_class, pred_conf, probs.detach().cpu()
        return cam_norm
