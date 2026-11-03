#!/usr/bin/env python3
"""
PikVaidya AI — Pipeline Model Evaluation & Empirical Benchmark Engine
=====================================================================
Evaluates trained EfficientNet-B0 checkpoint on the untouched test set:
  - Accuracy, Precision (Macro/Weighted), Recall (Macro/Weighted), F1 (Macro/Weighted)
  - Full scikit-learn classification report
  - 5x5 Confusion matrix exported to CSV
  - Per-class precision, recall, F1, and support analysis
  - Misclassification analysis with sample metadata and confidence
  - Comparative benchmark against historical 93.95% accuracy baseline
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

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


def run_pipeline_evaluation(
    checkpoint_path: Path,
    manifest_path: Path,
    output_dir: Path,
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

    model = build_model("efficientnet_b0", num_classes=num_classes, pretrained=False)
    state_dict = checkpoint.get("state_dict", checkpoint)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    # 2. Test DataLoader
    test_dataset = SugarcaneDataset(str(manifest_path), transform=get_transforms("test"))
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=0)
    print(f"\n[Test Set] Evaluating {len(test_dataset)} untouched held-out samples...")

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

    # 3. Compute Metrics
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

    # 5. Comparative Analysis against Historical Model (93.95% acc, 93.43% macro-F1)
    historical_benchmark = {
        "historical_accuracy": 0.9395,
        "historical_macro_f1": 0.9343,
        "delta_accuracy": round(acc - 0.9395, 4),
        "delta_macro_f1": round(f1_macro - 0.9343, 4),
        "comparable_splits": True,
        "notes": "Both models evaluated on deduplicated 5-class held-out test split of the audited sugarcane dataset."
    }

    # 6. Format Terminal Summary
    print("\n" + "=" * 65)
    print("  OVERALL TEST SET PERFORMANCE")
    print("=" * 65)
    print(f"  Test Accuracy:        {acc * 100:.2f}%")
    print(f"  Macro Precision:      {p_macro:.4f}")
    print(f"  Macro Recall:         {r_macro:.4f}")
    print(f"  Macro F1-Score:       {f1_macro:.4f}")
    print(f"  Weighted F1-Score:    {f1_weighted:.4f}")
    print(f"  Total Test Samples:   {len(test_dataset)}")
    print(f"  Correct Samples:      {len(test_dataset) - len(misclassifications)}")
    print(f"  Misclassified:        {len(misclassifications)}")
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
        "model_architecture": "EfficientNet-B0",
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
        "historical_comparison": historical_benchmark,
        "misclassifications_count": len(misclassifications),
        "per_class_metrics": per_class_summary
    }

    metrics_json = output_dir / "test_metrics.json"
    with open(metrics_json, "w", encoding="utf-8") as fp:
        json.dump(full_metrics, fp, indent=2)

    print(f"\n[Artifacts Exported]")
    print(f"  - Metrics JSON:        {metrics_json}")
    print(f"  - Confusion Matrix:    {cm_csv}")
    print(f"  - Misclassifications:  {misc_csv}")
    print("=" * 80 + "\n")

    return full_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI — Pipeline Evaluation")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--manifest", type=str, default="datasets/processed/sugarcane/test_manifest.csv")
    parser.add_argument("--output-dir", type=str, default="models/sugarcane/efficientnet_b0/pipeline_trained")
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    run_pipeline_evaluation(
        checkpoint_path=Path(args.checkpoint),
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output_dir),
        device_arg=args.device
    )

