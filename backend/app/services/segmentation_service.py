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

    def validate_foliar_quality(self, image: Image.Image) -> Tuple[bool, float, str]:
        """Validates that the uploaded image contains legitimate foliar vegetation.
        
        Uses HSV color-space bounds and Excess Green Index (ExG = 2G - R - B)
        to identify vegetation chlorophyll.
        
        Returns:
            Tuple of (is_valid, foliage_coverage_ratio, message)
        """
        rgb_img = image.convert("RGB")
        arr = np.array(rgb_img, dtype=float) / 255.0
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

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
    ) -> Tuple[DiagnosisSeverity, Optional[float]]:
        """Empirically segments foliar lesions and quantifies surface area percentage.
        
        Args:
            image: PIL Image of the crop leaf.
            predicted_class: Classification label ('Healthy', 'RedRot', 'Rust', 'Mosaic', 'Yellow').
            
        Returns:
            Tuple of (DiagnosisSeverity, affected_area_percentage).
        """
        if predicted_class == "Healthy":
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
        leaf_mask = (s > 0.10) & (v > 0.10)
        total_leaf_pixels = int(np.sum(leaf_mask))

        if total_leaf_pixels == 0:
            return DiagnosisSeverity.UNAVAILABLE, None

        # Segment pathological lesions based on target disease visual characteristics
        if predicted_class == "RedRot":
            # Red/brown necrotic lesions along midrib and blade
            lesion_mask = leaf_mask & (
                ((r > g * 1.05) & (s > 0.15)) | ((h < 26) & (s > 0.20)) | ((v < 0.25) & (s > 0.20))
            )
        elif predicted_class == "Rust":
            # Orange/reddish-brown powdery pustules
            lesion_mask = leaf_mask & (
                ((h < 35) & (s > 0.25) & (r > g)) | ((r > g * 1.08) & (s > 0.20))
            )
        elif predicted_class in ("Yellow", "Mosaic"):
            # Chlorosis: Yellowing, loss of chlorophyll (low ExG or shifted hue)
            lesion_mask = leaf_mask & (
                ((h >= 24) & (h <= 48) & (exg < 0.08)) | ((exg < -0.02) & (s > 0.15))
            )
        else:
            # Generic necrotic mask
            lesion_mask = leaf_mask & ((r > g * 1.05) | (h < 26))

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
            f"Foliar segmentation: {predicted_class} -> {affected_area}% affected foliage -> {severity.value}"
        )
        return severity, affected_area


segmentation_service = FoliarSegmentationService()
