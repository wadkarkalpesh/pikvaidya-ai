#!/usr/bin/env python3
"""
PikVaidya AI — Explainable AI (Grad-CAM) Saliency Visualization
==============================================================
Utilities for:
  - JET colormap rendering in pure NumPy (zero external dependencies)
  - Bilinear interpolation of activation maps to original resolution
  - Alpha-blended visual overlays for leaf pathology inspection
  - Multi-panel visual diagnostic reports for farmers and agronomists
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def jet_colormap(gray: np.ndarray) -> np.ndarray:
    """
    Converts a 2D scalar float array [0, 1] to an RGB uint8 array using
    the classic Jet colormap (Blue -> Cyan -> Green -> Yellow -> Red).
    """
    x = np.clip(gray, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    rgb = np.stack([r, g, b], axis=-1) * 255.0
    return np.clip(rgb, 0, 255).astype(np.uint8)


def generate_heatmap_image(cam_mask: np.ndarray, target_size: Optional[Tuple[int, int]] = None) -> Image.Image:
    """Generates standalone JET heatmap image from normalized CAM mask."""
    mask_uint8 = (np.clip(cam_mask, 0.0, 1.0) * 255.0).astype(np.uint8)
    mask_pil = Image.fromarray(mask_uint8, mode="L")
    if target_size:
        mask_pil = mask_pil.resize(target_size, Image.Resampling.BILINEAR)
    cam_interpolated = np.array(mask_pil, dtype=np.float32) / 255.0
    heatmap_arr = jet_colormap(cam_interpolated)
    return Image.fromarray(heatmap_arr, mode="RGB")


def apply_colormap_on_image(
    original_img: Image.Image,
    cam_mask: np.ndarray,
    output_path: Optional[Union[str, Path]] = None,
    alpha: float = 0.5,
    return_pair: bool = False
) -> Union[Image.Image, Tuple[Image.Image, Image.Image]]:
    """
    Resizes CAM mask to match original image dimensions using bilinear interpolation,
    applies the JET colormap, and creates an alpha-blended overlay.

    Args:
        original_img: Source PIL Image (RGB or convertible to RGB).
        cam_mask: 2D numpy array [0, 1] containing normalized Grad-CAM activations.
        output_path: Optional path to save the blended overlay image.
        alpha: Blending weight for heatmap overlay (0.0 = only image, 1.0 = only heatmap).
        return_pair: If False (default), returns overlay_img.
                     If True, returns tuple (heatmap_img, overlay_img).

    Returns:
        overlay_img OR (heatmap_img, overlay_img)
    """
    orig_rgb = original_img.convert("RGB")
    orig_w, orig_h = orig_rgb.size

    # Resize CAM mask to original image dimensions using high-quality bilinear interpolation
    mask_uint8 = (np.clip(cam_mask, 0.0, 1.0) * 255.0).astype(np.uint8)
    mask_pil = Image.fromarray(mask_uint8, mode="L").resize((orig_w, orig_h), Image.Resampling.BILINEAR)
    cam_interpolated = np.array(mask_pil, dtype=np.float32) / 255.0

    # Apply Jet colormap
    heatmap_arr = jet_colormap(cam_interpolated)
    heatmap_img = Image.fromarray(heatmap_arr, mode="RGB")

    # Alpha blending: blended = (1 - alpha) * original + alpha * heatmap
    orig_arr = np.array(orig_rgb, dtype=np.float32)
    blended_arr = (1.0 - alpha) * orig_arr + alpha * heatmap_arr.astype(np.float32)
    blended_arr = np.clip(blended_arr, 0.0, 255.0).astype(np.uint8)
    overlay_img = Image.fromarray(blended_arr, mode="RGB")

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        overlay_img.save(p)

    if return_pair:
        return heatmap_img, overlay_img
    return overlay_img


def create_explanation_summary(
    original_img: Image.Image,
    heatmap_img: Image.Image,
    overlay_img: Image.Image,
    prediction_info: Dict[str, Union[str, float, int, Dict[str, float]]],
    output_path: Optional[Path] = None,
    target_size: Tuple[int, int] = (256, 256)
) -> Image.Image:
    """
    Creates a publication-quality 4-panel diagnostic graphic:
      Panel 1: Original Leaf Image
      Panel 2: Grad-CAM Activation Heatmap
      Panel 3: Diagnostic Saliency Overlay
      Panel 4: Pathology Inference Diagnostic Card

    Args:
        original_img: Original PIL Image.
        heatmap_img: Standalone JET Heatmap PIL Image.
        overlay_img: Saliency Overlay PIL Image.
        prediction_info: Dict containing diagnostic metadata:
                         'predicted_class', 'confidence', 'actual_class',
                         'correct', 'target_layer', 'device', 'class_scores'.
        output_path: Optional Path to save composite image.
        target_size: Dimensions (width, height) to scale image panels for layout uniformity.

    Returns:
        composite: PIL Image of the 4-panel diagnostic card.
    """
    p_w, p_h = target_size
    margin = 16
    header_h = 44
    card_w = 340
    total_w = margin + (p_w + margin) * 3 + card_w + margin
    total_h = header_h + p_h + margin * 2

    composite = Image.new("RGB", (total_w, total_h), (245, 247, 250))
    draw = ImageDraw.Draw(composite)
    font = ImageFont.load_default()

    # Draw Top Application Banner
    draw.rectangle([(0, 0), (total_w, header_h)], fill=(24, 43, 73))
    draw.text(
        (margin, 12),
        "PikVaidya AI — Explainable Pathology Diagnosis Report (Grad-CAM Saliency Engine)",
        fill=(255, 255, 255),
        font=font
    )

    # Helper function to place an image panel with a title banner
    def place_panel(img: Image.Image, x_pos: int, title: str, subtitle: str):
        resized = img.convert("RGB").resize((p_w, p_h), Image.Resampling.BILINEAR)
        # Background shadow / border box
        draw.rectangle([(x_pos - 2, header_h + margin - 2), (x_pos + p_w + 2, header_h + margin + p_h + 2)], fill=(210, 215, 220))
        composite.paste(resized, (x_pos, header_h + margin))
        # Overlay caption pill at bottom of image
        pill_h = 32
        pill_y = header_h + margin + p_h - pill_h
        draw.rectangle([(x_pos, pill_y), (x_pos + p_w, pill_y + pill_h)], fill=(15, 23, 42))
        draw.text((x_pos + 8, pill_y + 4), title, fill=(255, 255, 255), font=font)
        draw.text((x_pos + 8, pill_y + 18), subtitle, fill=(148, 163, 184), font=font)

    # Panel 1: Original Image
    actual_str = str(prediction_info.get("actual_class", "Unknown"))
    place_panel(original_img, margin, "1. Input Leaf Image", f"Actual: {actual_str}")

    # Panel 2: Heatmap
    place_panel(heatmap_img, margin + (p_w + margin), "2. Grad-CAM Heatmap", "Colormap: Jet [0..1]")

    # Panel 3: Overlay
    place_panel(overlay_img, margin + (p_w + margin) * 2, "3. Lesion Saliency Overlay", "Blend Ratio: Alpha=0.50")

    # Panel 4: Diagnostic Metadata Card
    card_x = margin + (p_w + margin) * 3
    card_y = header_h + margin
    card_h = p_h
    draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], fill=(255, 255, 255), outline=(203, 213, 225), width=2)

    # Card Title
    draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + 32)], fill=(30, 41, 59))
    draw.text((card_x + 10, card_y + 10), "4. MODEL INFERENCE AUDIT", fill=(255, 255, 255), font=font)

    # Content
    pred_cls = str(prediction_info.get("predicted_class", "N/A"))
    confidence = float(prediction_info.get("confidence", 0.0))
    is_correct = prediction_info.get("correct", None)
    device = str(prediction_info.get("device", "CPU")).upper()
    target_layer = str(prediction_info.get("target_layer", "features[-1]"))

    y_cur = card_y + 40
    # Prediction Status Pill
    if is_correct is True:
        status_color = (22, 101, 52)   # Dark Green
        bg_color = (220, 252, 231)      # Light Green
        status_text = "VERIFIED MATCH (Correct)"
    elif is_correct is False:
        status_color = (153, 27, 27)   # Dark Red
        bg_color = (254, 226, 226)      # Light Red
        status_text = "MISCLASSIFICATION DETECTED"
    else:
        status_color = (30, 41, 59)
        bg_color = (241, 245, 249)
        status_text = "UNLABELED FIELD SAMPLE"

    draw.rectangle([(card_x + 8, y_cur), (card_x + card_w - 8, y_cur + 24)], fill=bg_color, outline=status_color)
    draw.text((card_x + 14, y_cur + 6), status_text, fill=status_color, font=font)
    y_cur += 32

    # Primary Diagnosis & Confidence
    draw.text((card_x + 10, y_cur), f"Predicted: {pred_cls}", fill=(15, 23, 42), font=font)
    y_cur += 16
    draw.text((card_x + 10, y_cur), f"Confidence: {confidence * 100:.2f}%", fill=(15, 23, 42), font=font)
    y_cur += 16
    draw.text((card_x + 10, y_cur), f"Execution Hardware: {device}", fill=(71, 85, 105), font=font)
    y_cur += 16
    draw.text((card_x + 10, y_cur), f"Target Conv Layer: {target_layer}", fill=(71, 85, 105), font=font)
    y_cur += 22

    # Per-Class Probability Bars
    draw.text((card_x + 10, y_cur), "Class Probabilities Distribution:", fill=(30, 41, 59), font=font)
    y_cur += 16

    class_scores = prediction_info.get("class_scores", {})
    if isinstance(class_scores, dict) and class_scores:
        bar_max_w = card_w - 110
        for cname, score in class_scores.items():
            prob = float(score)
            bar_w = int(max(2, prob * bar_max_w))
            # Label
            draw.text((card_x + 10, y_cur + 1), f"{cname[:8]:<8}", fill=(51, 65, 85), font=font)
            # Background track
            draw.rectangle([(card_x + 65, y_cur + 3), (card_x + 65 + bar_max_w, y_cur + 11)], fill=(226, 232, 240))
            # Filled bar
            bar_color = (37, 99, 235) if cname == pred_cls else (148, 163, 184)
            draw.rectangle([(card_x + 65, y_cur + 3), (card_x + 65 + bar_w, y_cur + 11)], fill=bar_color)
            # Score percent
            draw.text((card_x + 65 + bar_max_w + 6, y_cur + 1), f"{prob*100:4.1f}%", fill=(51, 65, 85), font=font)
            y_cur += 15

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composite.save(output_path)

    return composite
