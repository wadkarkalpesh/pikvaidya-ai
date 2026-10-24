import io
import os
import sys
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

import torch
import torch.nn as nn
from PIL import Image
import torchvision.transforms as T
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Standard ImageNet normalization parameters (exact match to training)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class ModelNotLoadedError(Exception):
    """Raised when an inference request is made but model is not loaded."""
    pass


class UnsupportedCropError(Exception):
    """Raised when an unsupported crop is requested."""
    pass


class InferenceError(Exception):
    """Raised when model forward pass or explanation generation fails."""
    pass


class ModelServingService:
    """Manages ML model lifecycle, singleton loading, image preprocessing,

    forward pass inference, and Grad-CAM explainability generation.
    """

    def __init__(self):
        self.model: Optional[nn.Module] = None
        self.device: torch.device = torch.device("cpu")
        self.class_to_idx: Dict[str, int] = {}
        self.idx_to_class: Dict[str, str] = {}
        self.model_name: str = "EfficientNet-B0"
        self.model_version: str = "EfficientNet-B0-v1.0"
        self.target_conv_layer: Optional[nn.Module] = None
        self.is_loaded: bool = False
        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

    def _resolve_project_root(self) -> Path:
        """Finds the root directory of the project where ML models/ resides."""
        # Check current working directory
        cwd = Path.cwd()
        if (cwd / "models" / "sugarcane").exists():
            return cwd
        # Check parent hierarchy (avoiding backend/app/models false match)
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "models" / "sugarcane").exists():
                return parent
        return cwd

    def _build_architecture(self, num_classes: int = 5) -> nn.Module:
        """Constructs EfficientNet-B0 configured identically to training."""
        from torchvision import models

        # Build architecture without downloading external weights
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, num_classes)
        )
        model.target_conv_layer = model.features[-1]
        model.arch_name = "EfficientNet-B0"
        return model

    def load_model(
        self,
        checkpoint_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
        force_reload: bool = False,
    ) -> None:
        """Loads model weights once at startup and reuses across requests."""
        if self.is_loaded and not force_reload:
            logger.info("Model already loaded. Reusing existing model instance.")
            return

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cpu")

        root = self._resolve_project_root()
        if checkpoint_path is None:
            resolved_ckpt = root / settings.MODEL_CHECKPOINT_PATH
        else:
            resolved_ckpt = Path(checkpoint_path)
            if not resolved_ckpt.is_absolute():
                resolved_ckpt = root / resolved_ckpt

        if not resolved_ckpt.exists():
            self.is_loaded = False
            raise FileNotFoundError(
                f"Model checkpoint not found at: {resolved_ckpt.resolve()}"
            )

        logger.info(f"Loading checkpoint from: {resolved_ckpt.resolve()} on {self.device}")
        checkpoint = torch.load(resolved_ckpt, map_location=self.device)

        # Extract class mapping
        if "idx_to_class" in checkpoint:
            self.idx_to_class = {str(k): str(v) for k, v in checkpoint["idx_to_class"].items()}
            self.class_to_idx = {str(k): int(v) for k, v in checkpoint["class_to_idx"].items()}
        else:
            # Fallback to standard sugarcane classes
            self.idx_to_class = {
                "0": "Healthy",
                "1": "Mosaic",
                "2": "RedRot",
                "3": "Rust",
                "4": "Yellow"
            }
            self.class_to_idx = {v: int(k) for k, v in self.idx_to_class.items()}

        num_classes = len(self.idx_to_class)
        self.model = self._build_architecture(num_classes=num_classes)
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.target_conv_layer = self.model.target_conv_layer
        self.model_name = checkpoint.get("model_name", "EfficientNet-B0")
        self.model_version = f"{self.model_name}-v1.0"
        self.is_loaded = True
        logger.info(f"Successfully loaded {self.model_version} with {num_classes} classes.")

    def preprocess_image(self, image: Union[Image.Image, bytes]) -> Tuple[torch.Tensor, Image.Image]:
        """Validates and preprocesses image into tensor matching training pipeline."""
        if isinstance(image, bytes):
            try:
                pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            except Exception as e:
                raise ValueError(f"Invalid image content: {e}")
        elif isinstance(image, Image.Image):
            pil_img = image.convert("RGB")
        else:
            raise TypeError("Image must be PIL.Image or bytes.")

        tensor = self.transform(pil_img)
        return tensor, pil_img

    def _generate_gradcam_heatmap(
        self,
        img_tensor: torch.Tensor,
        orig_img: Image.Image,
        target_class: int,
        save_path: Optional[Path] = None,
    ) -> np.ndarray:
        """Computes Grad-CAM activation heatmap with safe hook registration and removal."""
        gradients = []
        activations = []

        def forward_hook(module, input, output):
            activations.append(output)

        def backward_hook(module, grad_input, grad_output):
            gradients.append(grad_output[0])

        f_handle = self.target_conv_layer.register_forward_hook(forward_hook)
        b_handle = self.target_conv_layer.register_full_backward_hook(backward_hook)

        try:
            self.model.zero_grad()
            inp = img_tensor.unsqueeze(0).to(self.device).requires_grad_(True)
            output = self.model(inp)
            score = output[0, target_class]
            score.backward()

            if not gradients or not activations:
                raise RuntimeError("Grad-CAM hooks failed to capture activations/gradients.")

            grad = gradients[0].detach()
            act = activations[0].detach()

            weights = torch.mean(grad, dim=(2, 3), keepdim=True)
            cam = torch.sum(weights * act, dim=1, keepdim=True)
            cam = torch.clamp(cam, min=0)
            cam = cam.squeeze().cpu().numpy()

            cam_min, cam_max = cam.min(), cam.max()
            if cam_max > cam_min:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

            # Blend with original image
            if save_path:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                orig_w, orig_h = orig_img.size
                mask_img = Image.fromarray((cam * 255).astype(np.uint8)).resize(
                    (orig_w, orig_h), Image.Resampling.BILINEAR
                )
                mask_arr = np.array(mask_img, dtype=float) / 255.0

                r = np.clip(1.5 - np.abs(2.0 * mask_arr - 1.0), 0.0, 1.0)
                g = np.clip(1.5 - np.abs(2.0 * mask_arr - 0.5), 0.0, 1.0)
                b = np.clip(1.5 - np.abs(2.0 * mask_arr - 0.0), 0.0, 1.0)
                heatmap = np.stack([r, g, b], axis=-1) * 255.0

                orig_arr = np.array(orig_img, dtype=float)
                blended = 0.5 * orig_arr + 0.5 * heatmap
                blended = np.clip(blended, 0, 255).astype(np.uint8)
                Image.fromarray(blended).save(save_path, format="JPEG", quality=90)

            return cam
        finally:
            f_handle.remove()
            b_handle.remove()

    def predict(
        self,
        image: Union[Image.Image, bytes],
        crop: str = "sugarcane",
        generate_gradcam: bool = False,
        save_heatmap: bool = True,
    ) -> Dict[str, Any]:
        """Runs end-to-end inference on the input image."""
        if not self.is_loaded:
            # Try lazy loading
            try:
                self.load_model()
            except Exception as e:
                raise ModelNotLoadedError(f"Model service is unavailable: {e}")

        normalized_crop = crop.strip().lower()
        if normalized_crop != "sugarcane":
            raise UnsupportedCropError(
                f"Model currently only serves sugarcane crop pathology. Received: '{crop}'."
            )

        tensor, orig_img = self.preprocess_image(image)

        # Model forward pass
        try:
            with torch.no_grad():
                inp = tensor.unsqueeze(0).to(self.device)
                logits = self.model(inp)
                probs = torch.softmax(logits, dim=1).squeeze(0)
        except Exception as e:
            raise InferenceError(f"Model forward pass execution failed: {e}")

        pred_idx = int(torch.argmax(probs).item())
        predicted_class = self.idx_to_class.get(str(pred_idx), f"Class_{pred_idx}")
        confidence = float(probs[pred_idx].item())

        class_scores = {
            self.idx_to_class.get(str(i), f"Class_{i}"): round(float(probs[i].item()), 4)
            for i in range(len(probs))
        }

        # Explainability Grad-CAM handling
        explanation_status = "available"
        heatmap_rel_path = None

        if generate_gradcam:
            try:
                heatmap_dir = Path(settings.UPLOAD_DIR) / "heatmaps"
                heatmap_filename = f"cam_{uuid.uuid4().hex[:12]}_{predicted_class.lower()}.jpg"
                save_dest = (heatmap_dir / heatmap_filename) if save_heatmap else None

                self._generate_gradcam_heatmap(
                    img_tensor=tensor,
                    orig_img=orig_img,
                    target_class=pred_idx,
                    save_path=save_dest,
                )
                explanation_status = "generated"
                if save_dest:
                    heatmap_rel_path = str(save_dest).replace("\\", "/")
            except Exception as cam_err:
                logger.warning(f"Grad-CAM generation warning: {cam_err}")
                explanation_status = f"failed: {str(cam_err)}"

        return {
            "crop": "sugarcane",
            "predicted_class": predicted_class,
            "confidence": round(confidence, 4),
            "class_scores": class_scores,
            "model_version": self.model_version,
            "explanation_status": explanation_status,
            "heatmap_path": heatmap_rel_path,
        }


# Global singleton instance
model_service = ModelServingService()
