#!/usr/bin/env python3
"""
PikVaidya AI — Master Experiment Runner & Model Benchmark Suite
==============================================================
Orchestrates training, evaluation, calibration, and Grad-CAM for:
 - Model A: EfficientNet-B0
 - Model B: MobileNetV3-Large
 - Optional Baseline: ResNet-50
Aggregates empirical results into datasets/reports/model_comparison_benchmark.csv
"""

import os
import sys
import csv
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
from PIL import Image

from src.training.train import run_training
from src.evaluation.evaluate import run_evaluation
from src.training.models import build_model


def count_parameters(model: nn.Module) -> float:
    """Returns total trainable parameters in millions."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6


def run_full_suite(
    models_to_run: List[str],
    data_dir: Path,
    reports_dir: Path,
    epochs: int = 5,
    batch_size: int = 32,
    lr: float = 5e-4
):
    """Executes the full experiment suite across all selected architectures."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    benchmark_records = []

    print("\n" + "=" * 80)
    print("  PIKVAIDYA AI: MULTI-MODEL EXPERIMENT & BENCHMARK SUITE")
    print(f"  Target Crop: Sugarcane (5 Audited Classes) | Epochs: {epochs}")
    print(f"  Models: {', '.join(models_to_run)}")
    print("=" * 80)

    for model_key in models_to_run:
        print(f"\n>>> [STARTING EXPERIMENT: {model_key.upper()}] <<<")
        model_out_dir = Path(f"models/sugarcane/{model_key}")
        
        # 1. Train Model
        run_training(
            model_name=model_key,
            data_dir=data_dir,
            output_dir=model_out_dir,
            epochs=epochs,
            batch_size=batch_size,
            lr=lr
        )

        # 2. Evaluate Model & Generate Grad-CAM
        chk_path = model_out_dir / "best_model.pth"
        if not chk_path.exists():
            print(f"[Error] Checkpoint not found at {chk_path}")
            continue

        run_evaluation(
            model_name=model_key,
            checkpoint_path=chk_path,
            manifest_path=data_dir / "test_manifest.csv",
            output_dir=reports_dir,
            generate_xai=True
        )

        # 3. Read Test Metrics JSON
        res_json = reports_dir / f"test_metrics_{model_key}.json"
        with open(res_json, "r", encoding="utf-8") as f:
            test_results = json.load(f)

        perf = test_results["classification_performance"]
        calib = test_results["calibration"]

        # Calculate inference latency
        dummy_model = build_model(model_key, num_classes=5, pretrained=False)
        params_m = round(count_parameters(dummy_model), 2)

        benchmark_records.append({
            "Experiment": model_key,
            "Architecture": test_results["model_architecture"],
            "Parameters_M": params_m,
            "Test_Accuracy_Pct": round(perf["accuracy"] * 100, 2),
            "Macro_Precision": perf["macro_precision"],
            "Macro_Recall": perf["macro_recall"],
            "Macro_F1_Score": perf["macro_f1"],
            "Calibration_ECE": calib["expected_calibration_error_ece"],
            "Field_Testing_Acc_Pct": round(test_results["field_testing_summary"]["field_accuracy"] * 100, 2),
            "Artifact_Directory": str(model_out_dir)
        })

    # Save benchmark CSV
    benchmark_csv = reports_dir / "model_comparison_benchmark.csv"
    if benchmark_records:
        with open(benchmark_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(benchmark_records[0].keys()))
            writer.writeheader()
            writer.writerows(benchmark_records)

        print("\n" + "=" * 80)
        print("  PIKVAIDYA AI: FINAL EMPIRICAL BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"{'Model':<22}{'Params (M)':<12}{'Accuracy':<12}{'Macro F1':<12}{'Calib ECE':<12}")
        print("-" * 80)
        for r in benchmark_records:
            print(f"{r['Architecture']:<22}{r['Parameters_M']:<12}{r['Test_Accuracy_Pct']:<12}%{r['Macro_F1_Score']:<12}{r['Calibration_ECE']:<12}")
        print("-" * 80)
        print(f"[SUCCESS] Multi-model benchmark saved to: {benchmark_csv.name}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI Master Runner")
    parser.add_argument("--models", nargs="+", default=["efficientnet_b0", "mobilenet_v3"], help="Models to benchmark")
    parser.add_argument("--data-dir", type=str, default="datasets/processed/sugarcane")
    parser.add_argument("--reports-dir", type=str, default="datasets/reports")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-4)
    args = parser.parse_args()

    run_full_suite(
        models_to_run=args.models,
        data_dir=Path(args.data_dir),
        reports_dir=Path(args.reports_dir),
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr
    )
