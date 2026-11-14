"""PikVaidya AI — Foliar Lesion Segmentation & Foliage Quality Validator
=====================================================================
Provides empirical computer-vision-based foliar analysis using color-space
decomposition (HSV and Excess Green Index ExG) in pure NumPy/PIL.

Capabilities:
1. Out-of-Distribution (OOD) Foliage Quality Verification:
   Ensures uploaded imagery represents legitimate crop foliage, rejecting
   blank images, non-plant objects, and invalid files early.

2. Foliar Lesion Segmentation & Severity Quantification:
   Calculates actual necrosis/chlorosis surface area percentage relative
   to total foliage area, replacing hardcoded heuristics with empirical measurements.
   Supports both Sugarcane (5 classes) and Tomato (10 classes) pathology domains.
"""

import logging
from typing import Tuple, Optional
from PIL import Image
import numpy as np

from app.models.diagnosis import DiagnosisSeverity

logger = logging.getLogger(__name__)


class FoliarSegmentationService:
    """Performs empirical vegetation segmentation and lesion area quantification."""

    # Minimum percentage of total image pixels that must match foliage color signature
    MIN_FOLIAGE_THRESHOLD: float = 0.05  # 5%
    MIN_RESOLUTION_PX: int = 150
    MAX_RESOLUTION_PX: int = 6000
    BLUR_VARIANCE_THRESHOLD: float = 65.0  # Laplacian variance threshold

    def evaluate_blur_score(self, image: Image.Image) -> float:
        """Calculates sharpness using 2D discrete Laplacian variance in pure NumPy.
        
        A lower variance indicates a lack of high-frequency edges (blurry/out-of-focus image).
        """
        # Resize large image to standardized dimensions for consistent blur thresholding
        resized = image.convert("L").resize((400, 400), Image.Resampling.BILINEAR)
        gray = np.array(resized, dtype=float)
        
        # 3x3 Discrete Laplacian kernel [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
        laplacian = (
            gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
            - 4.0 * gray[1:-1, 1:-1]
        )
        return float(np.var(laplacian))

    def evaluate_lighting(self, image: Image.Image) -> Tuple[bool, float, str]:
        """Evaluates whether image lighting is sufficient for diagnostic pathology.
        
        Returns:
            Tuple of (is_acceptable, mean_brightness, description)
        """
        gray = np.array(image.convert("L"), dtype=float)
        mean_brightness = float(np.mean(gray) / 255.0)
        underexposed_ratio = float(np.mean(gray < 30.0))
        overexposed_ratio = float(np.mean(gray > 230.0))

        if mean_brightness < 0.14 or underexposed_ratio > 0.72:
            return False, mean_brightness, "Severe underexposure: The photo is too dark to resolve pathological symptoms. Please take the photo in well-lit natural daylight."
        if mean_brightness > 0.89 or overexposed_ratio > 0.65:
            return False, mean_brightness, "Severe overexposure: The photo is washed out by direct flash or glare. Please avoid direct sunlight reflections."

        return True, mean_brightness, "Lighting is acceptable."

    def validate_image_quality(self, image: Image.Image) -> Tuple[bool, str, dict]:
        """Performs comprehensive responsible AI image quality assessment.
        
        Evaluates:
        1. Dimension / Resolution boundaries
        2. Blurriness / Camera focus via Laplacian edge variance
        3. Lighting / Luminance distribution (avoiding severe underexposure/glare)
        4. Foliar vegetation coverage via HSV / Excess Green Index
        
        Returns:
            Tuple of (is_valid, message, metrics_dict)
        """
        width, height = image.size
        metrics = {
            "width": width,
            "height": height,
            "blur_variance": 0.0,
            "mean_brightness": 0.0,
            "foliage_coverage": 0.0,
        }

        # 1. Dimension validation
        if width < self.MIN_RESOLUTION_PX or height < self.MIN_RESOLUTION_PX:
            msg = (
                f"Image resolution too low ({width}x{height}px). Minimum required is "
                f"{self.MIN_RESOLUTION_PX}x{self.MIN_RESOLUTION_PX}px to discern foliar micro-lesions."
            )
            return False, msg, metrics
        if width > self.MAX_RESOLUTION_PX or height > self.MAX_RESOLUTION_PX:
            msg = f"Image dimensions ({width}x{height}px) exceed maximum allowed {self.MAX_RESOLUTION_PX}px."
            return False, msg, metrics

        # 2. Lighting validation
        is_light_ok, brightness, light_msg = self.evaluate_lighting(image)
        metrics["mean_brightness"] = round(brightness, 3)
        if not is_light_ok:
            return False, light_msg, metrics

        # 3. Sharpness / Blur validation
        blur_score = self.evaluate_blur_score(image)
        metrics["blur_variance"] = round(blur_score, 2)
        if blur_score < self.BLUR_VARIANCE_THRESHOLD:
            msg = (
                f"Image rejected: Photo appears blurry or out of focus (sharpness score {blur_score:.1f} < "
                f"threshold {self.BLUR_VARIANCE_THRESHOLD}). Please retake a clear, steady close-up photo of the crop leaf."
            )
            return False, msg, metrics

        # 4. Foliar vegetation presence validation
        is_foliar, coverage, foliar_msg = self.validate_foliar_quality(image)
        metrics["foliage_coverage"] = round(coverage, 3)
        if not is_foliar:
            return False, foliar_msg, metrics

        return True, "Image passes all agricultural quality and foliar presence criteria.", metrics

    def validate_foliar_quality(self, image: Image.Image) -> Tuple[bool, float, str]:
        """Validates that the uploaded image contains legitimate foliar vegetation.
        
        Uses HSV color-space bounds and Excess Green Index (ExG = 2G - R - B)
        to identify vegetation chlorophyll.
        
        Returns:
            Tuple of (is_valid, foliage_coverage_ratio, message)
        """
        rgb_img = image.convert("RGB")
        arr = np.array(rgb_img, dtype=float) / 255.0

        hsv_img = rgb_img.convert("HSV")
        hsv_arr = np.array(hsv_img, dtype=float)
        # PIL HSV: H in [0, 255] (corresponds to 0-360 deg), S in [0, 255], V in [0, 255]
        h = hsv_arr[..., 0]
        s = hsv_arr[..., 1] / 255.0
        v = hsv_arr[..., 2] / 255.0

        # Foliar vegetation signature:
        # Non-degenerate saturation & brightness, with hue in yellowish-green to deep green band
        foliage_mask = (s > 0.12) & (v > 0.12) & (h > 12) & (h < 125)
        foliage_pixels = np.sum(foliage_mask)
        total_pixels = arr.shape[0] * arr.shape[1]
        coverage_ratio = float(foliage_pixels / max(total_pixels, 1))

        if coverage_ratio < self.MIN_FOLIAGE_THRESHOLD:
            msg = (
                f"Image rejected: Foliar coverage ({coverage_ratio:.1%}) is below the minimum required "
                f"threshold ({self.MIN_FOLIAGE_THRESHOLD:.0%}). Please upload a clear photo centered on crop foliage."
            )
            return False, coverage_ratio, msg

        return True, coverage_ratio, "Valid foliar vegetation confirmed."

    def estimate_foliar_severity(
        self,
        image: Image.Image,
        predicted_class: str,
        crop: Optional[str] = None,
    ) -> Tuple[DiagnosisSeverity, Optional[float]]:
        """Empirically segments foliar lesions and quantifies surface area percentage.
        
        Args:
            image: PIL Image of the crop leaf.
            predicted_class: Classification label (Sugarcane or Tomato class).
            crop: Optional crop identifier ('sugarcane', 'tomato').
            
        Returns:
            Tuple of (DiagnosisSeverity, affected_area_percentage).
        """
        norm_class = predicted_class.strip().lower()
        if "healthy" in norm_class:
            return DiagnosisSeverity.HEALTHY, 0.0

        rgb_img = image.convert("RGB")
        arr = np.array(rgb_img, dtype=float) / 255.0
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        exg = 2 * g - r - b

        hsv_img = rgb_img.convert("HSV")
        hsv_arr = np.array(hsv_img, dtype=float)
        h = hsv_arr[..., 0]
        s = hsv_arr[..., 1] / 255.0
        v = hsv_arr[..., 2] / 255.0

        # Segment total leaf blade (both healthy green tissue and necrotic lesions)
        # Excludes non-foliar neutral background
        leaf_mask = (s > 0.08) & (v > 0.08)
        total_leaf_pixels = int(np.sum(leaf_mask))

        if total_leaf_pixels == 0:
            return DiagnosisSeverity.UNAVAILABLE, None

        # ----------------------------------------------------------------------
        # Target Pathological Lesion Segmentation
        # ----------------------------------------------------------------------
        # Sugarcane: Red Rot
        if "redrot" in norm_class or "red_rot" in norm_class:
            lesion_mask = leaf_mask & (
                ((r > g * 1.05) & (s > 0.15)) | ((h < 26) & (s > 0.20)) | ((v < 0.25) & (s > 0.20))
            )
        # Sugarcane: Rust
        elif "rust" in norm_class:
            lesion_mask = leaf_mask & (
                ((h < 35) & (s > 0.25) & (r > g)) | ((r > g * 1.08) & (s > 0.20))
            )
        # Sugarcane: Yellow Leaf Disease / Mosaic
        elif norm_class in ("yellow", "mosaic") or ("sugarcane" in (crop or "").lower() and "yellow" in norm_class):
            lesion_mask = leaf_mask & (
                ((h >= 24) & (h <= 48) & (exg < 0.08)) | ((exg < -0.02) & (s > 0.15))
            )
        # Tomato: Bacterial Spot
        elif "bacterial" in norm_class:
            # Dark brown to black circular lesions often with chlorotic halos
            lesion_mask = leaf_mask & (
                ((v < 0.30) & (s > 0.15)) | ((r > g * 1.05) & (v < 0.40)) | ((h >= 24) & (h <= 48) & (exg < 0.05))
            )
        # Tomato: Early Blight / Target Spot
        elif "early_blight" in norm_class or "target_spot" in norm_class:
            # Concentric dark rings with chlorosis
            lesion_mask = leaf_mask & (
                ((h < 32) & (s > 0.18) & (r > g)) | ((exg < 0.04) & (h < 46))
            )
        # Tomato: Late Blight
        elif "late_blight" in norm_class:
            # Water-soaked rapidly expanding dark necrotic patches
            lesion_mask = leaf_mask & (
                ((v < 0.35) & (s > 0.10)) | ((r > g * 1.02) & (v < 0.45))
            )
        # Tomato: Septoria Leaf Spot
        elif "septoria" in norm_class:
            # Small spots with dark borders and grey/tan centers
            lesion_mask = leaf_mask & (
                ((s < 0.18) & (v > 0.30) & (v < 0.70)) | ((v < 0.28) & (s > 0.10))
            )
        # Tomato: Leaf Mold
        elif "leaf_mold" in norm_class:
            # Pale yellow chlorotic spots and olive velvety patches
            lesion_mask = leaf_mask & (
                ((h >= 26) & (h <= 55) & (exg < 0.06)) | ((v < 0.38) & (s < 0.35))
            )
        # Tomato: Spider Mites
        elif "spider_mites" in norm_class:
            # Yellow stippling, chlorosis, and bronzing
            lesion_mask = leaf_mask & (
                ((exg < 0.03) & (h < 50) & (s > 0.12)) | ((h >= 20) & (h <= 45) & (r > g * 0.95))
            )
        # Tomato: Yellow Leaf Curl Virus
        elif "curl" in norm_class or "yellow_leaf_curl" in norm_class:
            # Intense upward curling and chlorosis of margins
            lesion_mask = leaf_mask & (
                ((h >= 22) & (h <= 52) & (exg < 0.06)) | ((exg < -0.01) & (s > 0.12))
            )
        # Tomato / Generic Mosaic Virus
        elif "mosaic" in norm_class:
            # Light green to yellow mottling
            lesion_mask = leaf_mask & (
                ((exg < 0.05) & (h < 50)) | ((h >= 25) & (h <= 48) & (exg < 0.08))
            )
        # Onion: Purple Blotch
        elif "purple_blotch" in norm_class or "blotch" in norm_class:
            lesion_mask = leaf_mask & (
                ((h < 30) & (s > 0.15) & (r > g)) | ((exg < 0.04) & (h < 45))
            )
        # Onion: Stemphylium Leaf Blight
        elif "stemphylium" in norm_class or "stemphylium_blight" in norm_class:
            lesion_mask = leaf_mask & (
                ((v < 0.35) & (s > 0.10)) | ((h >= 24) & (h <= 48) & (exg < 0.06))
            )
        # Onion: Iris Yellow Spot Virus
        elif "iris_yellow" in norm_class or "iris" in norm_class:
            lesion_mask = leaf_mask & (
                ((h >= 22) & (h <= 52) & (exg < 0.06)) | ((exg < -0.01) & (s > 0.10))
            )
        else:
            # Universal necrotic mask fallback
            lesion_mask = leaf_mask & ((r > g * 1.05) | (h < 26) | (v < 0.28))

        lesion_pixels = int(np.sum(lesion_mask))
        raw_percentage = (lesion_pixels / total_leaf_pixels) * 100.0

        # Constrain to plausible biological limits [1.0%, 95.0%] for confirmed diseases
        affected_area = float(np.clip(raw_percentage, 1.0, 95.0))
        affected_area = round(affected_area, 2)

        # Standard agronomic economic injury mapping:
        # Mild: < 10%
        # Moderate: 10% - 25%
        # Severe: > 25%
        if affected_area < 10.0:
            severity = DiagnosisSeverity.MILD
        elif affected_area < 25.0:
            severity = DiagnosisSeverity.MODERATE
        else:
            severity = DiagnosisSeverity.SEVERE

        logger.info(
            f"Foliar segmentation: {predicted_class} (crop={crop}) -> {affected_area}% affected foliage -> {severity.value}"
        )
        return severity, affected_area


segmentation_service = FoliarSegmentationService()
