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
    """Manages multi-crop ML model lifecycle, dynamic loading, image preprocessing,
    forward pass inference with temperature calibration, and Grad-CAM explainability.
    """

    CROP_REGISTRY: Dict[str, Dict[str, Any]] = {
        "sugarcane": {
            "checkpoint": "models/sugarcane/efficientnet_b0/pipeline_trained/best_model.pth",
            "onnx": "models/sugarcane/efficientnet_b0/model.onnx",
            "arch": "efficientnet_b0",
            "temperature": 1.2580,
            "display_name": "Sugarcane Pathology (EfficientNet-B0)"
        },
        "tomato": {
            "checkpoint": "models/tomato/mobilenet_v3/best_model.pth",
            "onnx": "models/tomato/mobilenet_v3/model.onnx",
            "arch": "mobilenet_v3",
            "temperature": 0.8350,
            "display_name": "Tomato Pathology (MobileNetV3-Large)"
        },
        "onion": {
            "checkpoint": "models/onion/mobilenet_v3/best_model.pth",
            "onnx": "models/onion/mobilenet_v3/model.onnx",
            "arch": "mobilenet_v3",
            "temperature": 2.2000,
            "display_name": "Onion Pathology (MobileNetV3-Large)"
        }
    }

    def __init__(self):
        # Multi-crop cache: maps crop_name -> model metadata dict
        self.crop_models: Dict[str, Dict[str, Any]] = {}
        self.onnx_sessions: Dict[str, Any] = {}
        self.device: torch.device = torch.device("cpu")

        # Backwards-compatibility aliases pointing to primary (sugarcane) model
        self.model: Optional[nn.Module] = None
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
        cwd = Path.cwd()
        if (cwd / "models" / "sugarcane").exists():
            return cwd
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "models" / "sugarcane").exists():
                return parent
        return cwd

    def _build_architecture(self, arch_type: str = "efficientnet_b0", num_classes: int = 5) -> nn.Module:
        """Constructs torchvision architecture configured identically to training."""
        from torchvision import models

        arch = arch_type.lower().replace("-", "_")
        if "mobilenet" in arch:
            model = models.mobilenet_v3_large(weights=None)
            in_features = model.classifier[0].in_features
            model.classifier = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.Hardswish(),
                nn.Dropout(p=0.2),
                nn.Linear(256, num_classes)
            )
            model.target_conv_layer = model.features[-1]
            model.arch_name = "MobileNetV3-Large"
        else:
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
        crop: str = "sugarcane",
    ) -> None:
        """Loads model weights for requested crop and reuses across requests."""
        normalized_crop = crop.strip().lower()
        if normalized_crop not in self.CROP_REGISTRY and checkpoint_path is None:
            raise UnsupportedCropError(f"Unsupported crop for model loading: '{crop}'.")

        if normalized_crop in self.crop_models and not force_reload and checkpoint_path is None:
            logger.info(f"Model for '{normalized_crop}' already loaded. Reusing cached instance.")
            return

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cpu")

        root = self._resolve_project_root()
        if checkpoint_path is None:
            rel_ckpt = self.CROP_REGISTRY[normalized_crop]["checkpoint"]
            resolved_ckpt = root / rel_ckpt
        else:
            resolved_ckpt = Path(checkpoint_path)
            if not resolved_ckpt.is_absolute():
                resolved_ckpt = root / resolved_ckpt

        if not resolved_ckpt.exists():
            if normalized_crop == "sugarcane":
                self.is_loaded = False
            raise FileNotFoundError(
                f"Model checkpoint not found at: {resolved_ckpt.resolve()}"
            )

        logger.info(f"Loading '{normalized_crop}' checkpoint from: {resolved_ckpt.resolve()} on {self.device}")
        checkpoint = torch.load(resolved_ckpt, map_location=self.device)

        # Extract class mapping
        if "idx_to_class" in checkpoint:
            idx_to_class = {str(k): str(v) for k, v in checkpoint["idx_to_class"].items()}
            class_to_idx = {str(k): int(v) for k, v in checkpoint["class_to_idx"].items()}
        else:
            idx_to_class = {"0": "Healthy", "1": "Mosaic", "2": "RedRot", "3": "Rust", "4": "Yellow"}
            class_to_idx = {v: int(k) for k, v in idx_to_class.items()}

        num_classes = len(idx_to_class)
        model_name = checkpoint.get("model_name", "EfficientNet-B0")

        # Determine architecture type from checkpoint or registry
        arch_type = "mobilenet_v3" if "mobilenet" in model_name.lower() else "efficientnet_b0"
        model = self._build_architecture(arch_type=arch_type, num_classes=num_classes)
        model.load_state_dict(checkpoint["state_dict"])
        model.to(self.device)
        model.eval()

        temp = self.CROP_REGISTRY.get(normalized_crop, {}).get("temperature", 1.0)
        crop_entry = {
            "model": model,
            "target_conv_layer": model.target_conv_layer,
            "idx_to_class": idx_to_class,
            "class_to_idx": class_to_idx,
            "model_name": model_name,
            "model_version": f"{model_name}-v1.0",
            "temperature": temp,
            "num_classes": num_classes,
        }
        self.crop_models[normalized_crop] = crop_entry

        # Populate legacy single-model attributes if sugarcane or primary
        if normalized_crop == "sugarcane" or not self.is_loaded:
            self.model = model
            self.idx_to_class = idx_to_class
            self.class_to_idx = class_to_idx
            self.model_name = model_name
            self.model_version = crop_entry["model_version"]
            self.target_conv_layer = model.target_conv_layer
            self.is_loaded = True

        logger.info(f"Successfully registered model for '{normalized_crop}' ({num_classes} classes, T*={temp}).")

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
        model: nn.Module,
        target_layer: nn.Module,
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

        f_handle = target_layer.register_forward_hook(forward_hook)
        b_handle = target_layer.register_full_backward_hook(backward_hook)

        try:
            model.zero_grad()
            inp = img_tensor.unsqueeze(0).to(self.device).requires_grad_(True)
            output = model(inp)
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

    def get_onnx_session(self, crop: str = "sugarcane"):
        """Loads and caches high-performance ONNX Runtime session."""
        import onnxruntime as ort
        normalized_crop = crop.strip().lower()
        if normalized_crop in self.onnx_sessions:
            return self.onnx_sessions[normalized_crop]
        
        root = self._resolve_project_root()
        onnx_rel = self.CROP_REGISTRY.get(normalized_crop, {}).get("onnx")
        if not onnx_rel:
            return None
        onnx_path = root / onnx_rel
        if not onnx_path.exists():
            return None
        
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.onnx_sessions[normalized_crop] = session
        return session

    def predict(
        self,
        image: Union[Image.Image, bytes],
        crop: str = "sugarcane",
        generate_gradcam: bool = False,
        save_heatmap: bool = True,
        use_onnx: bool = False,
    ) -> Dict[str, Any]:
        """Runs end-to-end inference on the input image using crop-specific registered model."""
        normalized_crop = crop.strip().lower()

        # Validate crop support
        if normalized_crop not in self.CROP_REGISTRY:
            supported_crops = ", ".join(self.CROP_REGISTRY.keys())
            raise UnsupportedCropError(
                f"Model currently only serves {supported_crops} crop pathology. Received: '{crop}'."
            )

        # Lazy-load crop model if not loaded
        if not self.is_loaded or normalized_crop not in self.crop_models:
            try:
                self.load_model(crop=normalized_crop)
            except Exception as e:
                raise ModelNotLoadedError(f"Model service for crop '{crop}' is unavailable: {e}")

        crop_entry = self.crop_models[normalized_crop]
        tensor, orig_img = self.preprocess_image(image)

        # Model forward pass with temperature scaling (ONNX or PyTorch)
        try:
            ort_session = self.get_onnx_session(normalized_crop) if (use_onnx and not generate_gradcam) else None
            if ort_session is not None:
                ort_inputs = {"input": tensor.unsqueeze(0).numpy()}
                raw_logits = ort_session.run(None, ort_inputs)[0]
                logits = torch.from_numpy(raw_logits)
            else:
                with torch.no_grad():
                    inp = tensor.unsqueeze(0).to(self.device)
                    logits = crop_entry["model"](inp)
            temp = crop_entry.get("temperature", 1.0)
            calibrated_logits = logits / max(temp, 1e-4)
            probs = torch.softmax(calibrated_logits, dim=1).squeeze(0)
        except Exception as e:
            raise InferenceError(f"Model forward pass execution failed: {e}")

        pred_idx = int(torch.argmax(probs).item())
        predicted_class = crop_entry["idx_to_class"].get(str(pred_idx), f"Class_{pred_idx}")
        confidence = float(probs[pred_idx].item())

        class_scores = {
            crop_entry["idx_to_class"].get(str(i), f"Class_{i}"): round(float(probs[i].item()), 4)
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
                    model=crop_entry["model"],
                    target_layer=crop_entry["target_conv_layer"],
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
            "crop": normalized_crop,
            "predicted_class": predicted_class,
            "confidence": round(confidence, 4),
            "class_scores": class_scores,
            "model_version": crop_entry["model_version"],
            "explanation_status": explanation_status,
            "heatmap_path": heatmap_rel_path,
        }


# Global singleton instance
model_service = ModelServingService()
