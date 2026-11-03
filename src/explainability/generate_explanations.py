#!/usr/bin/env python3
"""
PikVaidya AI — Grad-CAM Batch Explanation & Saliency CLI Engine
================================================================
Processes test dataset images through the trained sugarcane pathology classifier,
generating explainability heatmaps, visual overlays, and diagnostic reports.

Outputs:
  - outputs/gradcam/original/   (Raw input images)
  - outputs/gradcam/heatmaps/   (Standalone Jet activation heatmaps)
  - outputs/gradcam/overlays/   (Alpha-blended lesion overlays)
  - outputs/gradcam/reports/    (4-panel diagnostic cards & CSV summary)

Usage:
  python -m src.explainability.generate_explanations --num-samples 25
  python -m src.explainability.generate_explanations --device cpu --num-samples 25
"""

import os
import sys
import csv
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
import numpy as np
import torch
import torch.nn as nn

from src.training.models import build_model
from src.data.dataset import get_transforms
from src.explainability.gradcam import GradCAM
from src.explainability.visualization import apply_colormap_on_image, create_explanation_summary

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("PikVaidya_GradCAM")


def resolve_device(device_arg: str) -> Tuple[torch.device, str]:
    """
    Resolves execution hardware safely, respecting native GPU availability
    and falling back gracefully to CPU if CUDA runtime is unavailable.
    """
    if device_arg == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda"), "cuda"
        else:
            logger.warning("CUDA requested but torch.cuda.is_available() is False. Falling back to CPU.")
            return torch.device("cpu"), "cpu"
    elif device_arg == "cpu":
        return torch.device("cpu"), "cpu"
    else:  # "auto"
        if torch.cuda.is_available():
            return torch.device("cuda"), "cuda"
        else:
            return torch.device("cpu"), "cpu"


def find_checkpoint(user_path: Optional[str] = None) -> Path:
    """Finds best available trained checkpoint."""
    candidates = []
    if user_path:
        candidates.append(Path(user_path))
    candidates.extend([
        PROJECT_ROOT / "checkpoints" / "best_model.pth",
        PROJECT_ROOT / "models" / "sugarcane" / "efficientnet_b0" / "best_model.pth",
        PROJECT_ROOT / "models" / "sugarcane" / "mobilenet_v3" / "best_model.pth"
    ])
    for c in candidates:
        if c.exists() and c.is_file():
            return c.resolve()
    raise FileNotFoundError(
        f"No valid checkpoint found in searched paths: {[str(c) for c in candidates]}"
    )


def load_model_from_checkpoint(
    checkpoint_path: Path,
    device: torch.device,
    model_name: str = "efficientnet_b0"
) -> Tuple[nn.Module, Dict[int, str], Dict[str, int]]:
    """Loads model architecture and restores weights from checkpoint."""
    logger.info(f"Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    # Resolve class mappings
    if "idx_to_class" in checkpoint and "class_to_idx" in checkpoint:
        raw_i2c = checkpoint["idx_to_class"]
        idx_to_class = {int(k): str(v) for k, v in raw_i2c.items()}
        class_to_idx = {str(k): int(v) for k, v in checkpoint["class_to_idx"].items()}
    else:
        # Fallback default class ordering
        class_names = ["Healthy", "Mosaic", "RedRot", "Rust", "Yellow"]
        idx_to_class = {i: c for i, c in enumerate(class_names)}
        class_to_idx = {c: i for i, c in enumerate(class_names)}

    num_classes = len(idx_to_class)
    model = build_model(model_name, num_classes=num_classes, pretrained=False)
    
    state_dict = checkpoint.get("state_dict", checkpoint)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    return model, idx_to_class, class_to_idx


def select_diverse_test_batch(
    manifest_path: Path,
    model: nn.Module,
    device: torch.device,
    idx_to_class: Dict[int, str],
    min_samples: int = 25
) -> List[Dict]:
    """
    Selects a stratified and diverse batch of test images containing:
      1. Correctly classified samples for ALL 5 classes
      2. Misclassified samples across classes to analyze diagnostic failures
    """
    transform = get_transforms("test")
    rows = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    logger.info(f"Auditing {len(rows)} test set samples for diverse batch selection...")

    correct_by_class: Dict[str, List[Dict]] = {c: [] for c in idx_to_class.values()}
    misclassified_samples: List[Dict] = []

    with torch.no_grad():
        for r in rows:
            img_path = Path(r["image_path"])
            if not img_path.is_absolute():
                img_path = PROJECT_ROOT / img_path
            if not img_path.exists():
                continue

            actual_class = r["class_name"]
            with Image.open(img_path) as im:
                t = transform(im.convert("RGB")).unsqueeze(0).to(device)
                logits = model(t)
                probs = torch.softmax(logits, dim=1).squeeze(0)
                pred_idx = int(torch.argmax(logits, dim=1).item())
                pred_class = idx_to_class[pred_idx]
                conf = float(probs[pred_idx].item())

                sample_meta = {
                    "image_path": str(img_path),
                    "image_name": img_path.name,
                    "actual_class": actual_class,
                    "predicted_class": pred_class,
                    "predicted_idx": pred_idx,
                    "confidence": conf,
                    "correct": (pred_class == actual_class),
                    "class_scores": {idx_to_class[i]: float(probs[i].item()) for i in range(len(idx_to_class))}
                }

                if sample_meta["correct"]:
                    correct_by_class[actual_class].append(sample_meta)
                else:
                    misclassified_samples.append(sample_meta)

    # Build balanced selection
    selected_batch: List[Dict] = []
    
    # 1. Take 3-4 correct samples per class
    target_correct_per_class = max(3, (min_samples - 6) // len(idx_to_class))
    for cname, items in correct_by_class.items():
        # Sort items by confidence (take high, median, lower)
        sorted_items = sorted(items, key=lambda x: x["confidence"], reverse=True)
        take_count = min(target_correct_per_class, len(sorted_items))
        if take_count > 0:
            selected_batch.extend(sorted_items[:take_count])

    # 2. Add misclassified samples
    num_misclass_to_add = max(5, min_samples - len(selected_batch))
    selected_batch.extend(misclassified_samples[:num_misclass_to_add])

    # If still below min_samples, fill with remaining correct samples
    if len(selected_batch) < min_samples:
        for cname, items in correct_by_class.items():
            for item in items:
                if item not in selected_batch:
                    selected_batch.append(item)
                    if len(selected_batch) >= min_samples:
                        break
            if len(selected_batch) >= min_samples:
                break

    logger.info(
        f"Selected batch of {len(selected_batch)} samples "
        f"({sum(1 for s in selected_batch if s['correct'])} correct, "
        f"{sum(1 for s in selected_batch if not s['correct'])} misclassified)."
    )
    return selected_batch


def run_batch_explanation(
    checkpoint_path: Optional[str] = None,
    manifest_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    device_name: str = "auto",
    num_samples: int = 25,
    model_name: str = "efficientnet_b0",
    target_class: Optional[int] = None
) -> Dict:
    """
    Executes full batch Grad-CAM generation and produces structured artifacts.
    """
    ckpt_path = find_checkpoint(checkpoint_path)
    device, device_str = resolve_device(device_name)
    logger.info(f"Target Execution Hardware: {device_str.upper()} (Device object: {device})")

    out_root = Path(output_dir or (PROJECT_ROOT / "outputs" / "gradcam")).resolve()
    dir_orig = out_root / "original"
    dir_heat = out_root / "heatmaps"
    dir_over = out_root / "overlays"
    dir_repo = out_root / "reports"

    for d in [dir_orig, dir_heat, dir_over, dir_repo]:
        d.mkdir(parents=True, exist_ok=True)

    mpath = Path(manifest_path or (PROJECT_ROOT / "datasets" / "processed" / "sugarcane" / "test_manifest.csv")).resolve()
    if not mpath.exists():
        raise FileNotFoundError(f"Test manifest not found at: {mpath}")

    # 1. Load Model & Setup GradCAM
    model, idx_to_class, class_to_idx = load_model_from_checkpoint(ckpt_path, device, model_name=model_name)
    transform = get_transforms("test")

    # Select target layer
    target_conv_layer = getattr(model, "target_conv_layer", model.features[-1])
    target_layer_str = "features[-1]"

    # 2. Select diverse test samples
    samples = select_diverse_test_batch(mpath, model, device, idx_to_class, min_samples=num_samples)

    # 3. Process each sample with GradCAM
    records = []
    error_logs = []

    print("\n" + "=" * 80)
    print(f"  PIKVAIDYA AI: GRAD-CAM EXPLAINABILITY BATCH RUN")
    print(f"  Model: {model_name} | Hardware: {device_str.upper()} | Samples: {len(samples)}")
    print("=" * 80)

    with GradCAM(model, target_conv_layer) as gradcam:
        for idx, sample in enumerate(samples, 1):
            img_path = Path(sample["image_path"])
            stem = img_path.stem
            actual_cls = sample["actual_class"]

            try:
                with Image.open(img_path) as orig_img:
                    orig_rgb = orig_img.convert("RGB")
                    tensor = transform(orig_rgb).unsqueeze(0).to(device)

                    # Compute Grad-CAM
                    cam_mask, pred_idx, pred_conf, probs_tensor = gradcam.generate_cam(
                        tensor,
                        target_class=target_class,
                        return_details=True
                    )

                    pred_cls = idx_to_class[pred_idx]
                    is_correct = (pred_cls == actual_cls)

                    # Paths for artifacts
                    orig_save_path = dir_orig / f"{stem}_original.png"
                    heat_save_path = dir_heat / f"{stem}_heatmap.png"
                    over_save_path = dir_over / f"{stem}_overlay.png"
                    repo_save_path = dir_repo / f"{stem}_report.png"

                    # 1. Save Original
                    orig_rgb.save(orig_save_path)

                    # 2. Apply Colormap and save Heatmap & Overlay
                    heatmap_img, overlay_img = apply_colormap_on_image(orig_rgb, cam_mask, alpha=0.50, return_pair=True)
                    heatmap_img.save(heat_save_path)
                    overlay_img.save(over_save_path)

                    # 3. Create Multi-Panel Diagnostic Report
                    pred_info = {
                        "actual_class": actual_cls,
                        "predicted_class": pred_cls,
                        "confidence": pred_conf,
                        "correct": is_correct,
                        "device": device_str.upper(),
                        "target_layer": target_layer_str,
                        "class_scores": {idx_to_class[i]: float(probs_tensor[i].item()) for i in range(len(idx_to_class))}
                    }
                    create_explanation_summary(
                        orig_rgb,
                        heatmap_img,
                        overlay_img,
                        pred_info,
                        output_path=repo_save_path
                    )

                    # Record row for CSV
                    record = {
                        "image_name": img_path.name,
                        "actual_class": actual_cls,
                        "predicted_class": pred_cls,
                        "confidence": f"{pred_conf:.4f}",
                        "correct_prediction": "True" if is_correct else "False",
                        "target_layer": target_layer_str,
                        "execution_device": device_str.upper(),
                        "gradcam_output_path": str(over_save_path.relative_to(PROJECT_ROOT))
                    }
                    records.append(record)

                    status_mark = "[CORRECT]" if is_correct else "[MISCLASSIFIED]"
                    print(
                        f"[{idx:02d}/{len(samples):02d}] {stem[:28]:<28} "
                        f"Actual: {actual_cls:<8} | Pred: {pred_cls:<8} ({pred_conf*100:5.1f}%) "
                        f"{status_mark:<16} -> {over_save_path.name}"
                    )

            except Exception as e:
                err_msg = f"Failed processing {img_path.name}: {str(e)}"
                logger.error(err_msg, exc_info=True)
                error_logs.append(err_msg)

    # 4. Write CSV Report
    csv_report_path = dir_repo / "batch_explanation_report.csv"
    csv_headers = [
        "image_name",
        "actual_class",
        "predicted_class",
        "confidence",
        "correct_prediction",
        "target_layer",
        "execution_device",
        "gradcam_output_path"
    ]
    with open(csv_report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        for r in records:
            writer.writerow(r)

    # 5. Write Run Summary JSON
    summary_json_path = dir_repo / "batch_summary.json"
    summary_data = {
        "model_architecture": model_name,
        "checkpoint": str(ckpt_path),
        "target_layer": target_layer_str,
        "execution_device": device_str.upper(),
        "total_processed": len(records),
        "total_errors": len(error_logs),
        "correct_count": sum(1 for r in records if r["correct_prediction"] == "True"),
        "misclassified_count": sum(1 for r in records if r["correct_prediction"] == "False"),
        "csv_report": str(csv_report_path),
        "errors": error_logs
    }
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("=" * 80)
    print(f"[SUCCESS] Grad-CAM Batch Complete: {len(records)} explanations generated.")
    print(f"  CSV Report:    {csv_report_path}")
    print(f"  Summary JSON:  {summary_json_path}")
    print(f"  Overlays:      {dir_over}")
    print(f"  Reports:       {dir_repo}")
    print("=" * 80 + "\n")

    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI — Grad-CAM Batch Explanation CLI")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to best_model.pth")
    parser.add_argument("--manifest", type=str, default=None, help="Path to test_manifest.csv")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save artifacts")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"], help="Execution device")
    parser.add_argument("--num-samples", type=int, default=25, help="Number of diverse test samples to process")
    parser.add_argument("--model", type=str, default="efficientnet_b0", help="Model architecture")
    parser.add_argument("--target-class", type=int, default=None, help="Optional forced class index for CAM")
    args = parser.parse_args()

    run_batch_explanation(
        checkpoint_path=args.checkpoint,
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        device_name=args.device,
        num_samples=args.num_samples,
        model_name=args.model,
        target_class=args.target_class
    )
