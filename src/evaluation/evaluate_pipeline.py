#!/usr/bin/env python3
"""
PikVaidya AI — Pipeline Model Evaluation & Empirical Benchmark Engine
=====================================================================
Evaluates trained vision checkpoints (EfficientNet-B0, MobileNetV3-Large, ResNet-50)
on the untouched test set:
  - Accuracy, Precision (Macro/Weighted), Recall (Macro/Weighted), F1 (Macro/Weighted)
  - 5x5 Confusion matrix exported to CSV
  - Per-class precision, recall, F1, and support analysis
  - Misclassification analysis with sample metadata and confidence
  - Confidence calibration: Expected Calibration Error (ECE) and Temperature Scaling (T*)
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.data.dataset import SugarcaneDataset, get_transforms
from src.training.models import build_model
from src.evaluation.metrics import compute_classification_metrics
from src.evaluation.calibration import TemperatureScaler, evaluate_calibration


def run_pipeline_evaluation(
    checkpoint_path: Path,
    manifest_path: Path,
    output_dir: Path,
    val_manifest_path: Optional[Path] = None,
    arch: Optional[str] = None,
    device_arg: str = "auto"
) -> Dict[str, Any]:
    """Runs rigorous empirical evaluation on the held-out test set."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if device_arg == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    elif device_arg == "cpu":
        device = torch.device("cpu")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("\n" + "=" * 80)
    print("  PIKVAIDYA AI: PIPELINE EMPIRICAL TEST-SET EVALUATION")
    print(f"  Checkpoint: {checkpoint_path}")
    print(f"  Device:     {device}")
    print(f"  Test Data:  {manifest_path}")
    print("=" * 80)

    # 1. Load Checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device)
    class_to_idx = checkpoint["class_to_idx"]
    idx_to_class = checkpoint["idx_to_class"]
    class_names = [idx_to_class[str(i)] for i in range(len(class_to_idx))]
    num_classes = len(class_names)

    # Detect architecture
    arch_key = arch
    if not arch_key:
        ckpt_name = checkpoint.get("model_name", "").lower()
        if "mobilenet" in ckpt_name:
            arch_key = "mobilenet_v3"
        elif "resnet" in ckpt_name:
            arch_key = "resnet50"
        else:
            arch_key = "efficientnet_b0"

    model = build_model(arch_key, num_classes=num_classes, pretrained=False)
    state_dict = checkpoint.get("state_dict", checkpoint)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    arch_display = getattr(model, "arch_name", arch_key)

    # 2. Test DataLoader
    test_dataset = SugarcaneDataset(str(manifest_path), transform=get_transforms("test"))
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=0)
    print(f"\n[Test Set] Evaluating {len(test_dataset)} untouched held-out samples with {arch_display}...")

    all_preds, all_labels, all_probs, all_paths = [], [], [], []

    with torch.no_grad():
        for images, labels, paths in test_loader:
            images = images.to(device)
            logits = model(images)
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_probs.extend(probs.cpu().tolist())
            all_paths.extend(paths)

    # 3. Compute Classification Performance Metrics
    perf = compute_classification_metrics(all_labels, all_preds, class_names)
    acc = perf["accuracy"]
    p_macro = perf["macro_precision"]
    r_macro = perf["macro_recall"]
    f1_macro = perf["macro_f1"]
    f1_weighted = perf.get("weighted_f1", f1_macro)
    cm = perf["confusion_matrix"]
    per_class_summary = perf["per_class"]

    # 4. Misclassification Analysis
    misclassifications = []
    for idx, (lbl, pred) in enumerate(zip(all_labels, all_preds)):
        if lbl != pred:
            conf = float(all_probs[idx][pred])
            true_conf = float(all_probs[idx][lbl])
            misclassifications.append({
                "image_path": all_paths[idx],
                "image_name": Path(all_paths[idx]).name,
                "ground_truth": class_names[lbl],
                "predicted": class_names[pred],
                "predicted_confidence": round(conf, 4),
                "ground_truth_confidence": round(true_conf, 4)
            })

    # 5. Confidence Calibration (ECE & Temperature Scaling)
    if val_manifest_path is None:
        default_val = manifest_path.parent / "val_manifest.csv"
        if default_val.exists():
            val_manifest_path = default_val

    calib_metrics = None
    scaler = None
    if val_manifest_path and val_manifest_path.exists():
        print(f"\n[Calibration] Tuning Temperature Scaling on validation set ({val_manifest_path})...")
        val_dataset = SugarcaneDataset(str(val_manifest_path), transform=get_transforms("val"))
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=0)
        scaler = TemperatureScaler(initial_temp=1.0)
        opt_temp = scaler.fit(model, val_loader, device)

        calib_metrics = evaluate_calibration(model, scaler, test_loader, device, n_bins=10)
        calib_metrics["optimal_temperature"] = round(opt_temp, 4)

        calib_json = output_dir / "calibration_metrics.json"
        with open(calib_json, "w", encoding="utf-8") as fp:
            json.dump(calib_metrics, fp, indent=2)

    # 6. Format Terminal Summary
    print("\n" + "=" * 65)
    print(f"  OVERALL TEST SET PERFORMANCE: {arch_display.upper()}")
    print("=" * 65)
    print(f"  Test Accuracy:        {acc * 100:.2f}%")
    print(f"  Macro Precision:      {p_macro:.4f}")
    print(f"  Macro Recall:         {r_macro:.4f}")
    print(f"  Macro F1-Score:       {f1_macro:.4f}")
    print(f"  Weighted F1-Score:    {f1_weighted:.4f}")
    print(f"  Total Test Samples:   {len(test_dataset)}")
    print(f"  Correct Samples:      {len(test_dataset) - len(misclassifications)}")
    print(f"  Misclassified:        {len(misclassifications)}")
    if calib_metrics:
        print(f"  Uncalibrated ECE (T=1.0): {calib_metrics['uncalibrated']['ece']:.4f}")
        if 'calibrated' in calib_metrics:
            print(f"  Calibrated ECE (T={calib_metrics['optimal_temperature']:.3f}):   {calib_metrics['calibrated']['ece']:.4f} "
                  f"(Reduction: {calib_metrics['calibrated']['ece_reduction_pct']}%)")
    print("-" * 65)

    print("\n[Per-Class Performance Summary]")
    print(f"{'Class':<14}{'Precision':<12}{'Recall':<12}{'F1-Score':<12}{'Support':<10}")
    print("-" * 60)
    for cname, vals in per_class_summary.items():
        print(f"{cname:<14}{vals['precision']:<12.4f}{vals['recall']:<12.4f}{vals['f1_score']:<12.4f}{vals['support']:<10}")
    print("-" * 60)

    # 7. Save Confusion Matrix CSV
    cm_csv = output_dir / "confusion_matrix.csv"
    with open(cm_csv, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["True\\Pred"] + class_names)
        for i, row in enumerate(cm):
            writer.writerow([class_names[i]] + row)

    # 8. Save Misclassifications CSV
    misc_csv = output_dir / "misclassifications.csv"
    if misclassifications:
        with open(misc_csv, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=list(misclassifications[0].keys()))
            writer.writeheader()
            writer.writerows(misclassifications)

    # 9. Save Comprehensive JSON Metrics
    full_metrics = {
        "model_architecture": arch_display,
        "checkpoint": str(checkpoint_path),
        "test_samples": len(test_dataset),
        "overall": {
            "accuracy": round(float(acc), 4),
            "macro_precision": round(float(p_macro), 4),
            "macro_recall": round(float(r_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_f1": round(float(f1_weighted), 4)
        },
        "per_class": per_class_summary,
        "confusion_matrix": cm,
        "misclassifications_count": len(misclassifications),
        "calibration": calib_metrics
    }

    metrics_json = output_dir / "test_metrics.json"
    with open(metrics_json, "w", encoding="utf-8") as fp:
        json.dump(full_metrics, fp, indent=2)

    print(f"\n[Artifacts Exported]")
    print(f"  - Metrics JSON:        {metrics_json}")
    print(f"  - Confusion Matrix:    {cm_csv}")
    print(f"  - Misclassifications:  {misc_csv}")
    if calib_metrics:
        print(f"  - Calibration Metrics: {output_dir / 'calibration_metrics.json'}")
    print("=" * 80 + "\n")

    return full_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI — Pipeline Evaluation")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--arch", type=str, default=None)
    parser.add_argument("--manifest", type=str, default="datasets/processed/sugarcane/test_manifest.csv")
    parser.add_argument("--val-manifest", type=str, default="datasets/processed/sugarcane/val_manifest.csv")
    parser.add_argument("--output-dir", type=str, default="models/sugarcane/mobilenet_v3/pipeline_trained")
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    run_pipeline_evaluation(
        checkpoint_path=Path(args.checkpoint),
        manifest_path=Path(args.manifest),
        val_manifest_path=Path(args.val_manifest),
        output_dir=Path(args.output_dir),
        arch=args.arch,
        device_arg=args.device
    )
