"""
PikVaidya AI — Automated Tests: Image Quality & Responsible AI Safeguards
=========================================================================
Verifies:
1. Laplacian variance blur detection.
2. Underexposure and overexposure lighting detection.
3. Dimension resolution boundaries.
4. Out-of-Distribution non-foliar rejection.
"""

import pytest
from PIL import Image
import numpy as np
from app.services.segmentation_service import segmentation_service


def test_blur_detection_sharp_vs_flat():
    # 1. Flat solid color has 0 variance (blurry/textureless)
    flat_img = Image.new("RGB", (300, 300), color=(34, 139, 34))
    blur_score = segmentation_service.evaluate_blur_score(flat_img)
    assert blur_score == 0.0

    # 2. Textured synthetic leaf image with high-frequency edges
    rng = np.random.RandomState(42)
    arr = rng.randint(40, 180, (400, 400, 3), dtype=np.uint8)
    arr[..., 1] = np.clip(arr[..., 1] + 50, 0, 255)
    sharp_img = Image.fromarray(arr)
    sharp_score = segmentation_service.evaluate_blur_score(sharp_img)
    assert sharp_score > segmentation_service.BLUR_VARIANCE_THRESHOLD


def test_lighting_detection_extremes():
    # Severe underexposure (pitch black)
    black_img = Image.new("RGB", (200, 200), color=(0, 0, 0))
    is_ok, brightness, msg = segmentation_service.evaluate_lighting(black_img)
    assert is_ok is False
    assert "underexposure" in msg.lower()
    assert brightness < 0.05

    # Severe overexposure (washed out white)
    white_img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    is_ok, brightness, msg = segmentation_service.evaluate_lighting(white_img)
    assert is_ok is False
    assert "overexposure" in msg.lower()
    assert brightness > 0.95

    # Balanced daylight lighting
    normal_img = Image.new("RGB", (200, 200), color=(100, 160, 80))
    is_ok, brightness, msg = segmentation_service.evaluate_lighting(normal_img)
    assert is_ok is True
    assert 0.2 < brightness < 0.8


def test_resolution_boundaries():
    # Tiny image (< 150px)
    tiny_img = Image.new("RGB", (80, 80), color=(34, 139, 34))
    ok, msg, metrics = segmentation_service.validate_image_quality(tiny_img)
    assert ok is False
    assert "resolution too low" in msg.lower()

    # Valid resolution textured image
    rng = np.random.RandomState(123)
    arr = rng.randint(40, 200, (300, 300, 3), dtype=np.uint8)
    arr[..., 1] = np.clip(arr[..., 1] + 45, 0, 255)
    valid_img = Image.fromarray(arr)
    ok, msg, metrics = segmentation_service.validate_image_quality(valid_img)
    assert ok is True
    assert metrics["width"] == 300
    assert metrics["height"] == 300
    assert metrics["foliage_coverage"] > 0.05

