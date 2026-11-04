#!/usr/bin/env python3
"""
PikVaidya AI — Confidence Calibration & Temperature Scaling Engine
==================================================================
Implements post-processing probability calibration using Temperature Scaling
(Guo et al., 2017 - "On Calibration of Modern Neural Networks").

Calibration Formula:
    p_i = exp(z_i / T) / sum_j exp(z_j / T)

Where:
    - z_i are unnormalized logit outputs for class i
    - T > 0 is the learned scalar temperature
    - T > 1.0 softens overconfident probabilities (reduces overconfidence)
    - T < 1.0 sharpens underconfident probabilities

Features:
    - Non-destructive: model weights remain strictly frozen
    - Preserves classification accuracy (argmax is invariant to positive scaling)
    - L-BFGS optimization of Negative Log-Likelihood (NLL) on validation logits
    - Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)
    - Reliability diagram bin details export
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.evaluation.metrics import compute_calibration_ece


class TemperatureScaler(nn.Module):
    """
    Learns and applies Temperature Scaling to model logits.
    """

    def __init__(self, initial_temp: float = 1.0):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * initial_temp)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """Scales logits by temperature: z / T."""
        return logits / self.temperature.clamp(min=0.01)

    def fit(
        self,
        model: nn.Module,
        val_loader: DataLoader,
        device: torch.device,
        max_iter: int = 50,
        lr: float = 0.01
    ) -> float:
        """
        Tunes temperature parameter on validation set to minimize NLL.
        Model weights are kept strictly frozen.
        """
        model.eval()
        logits_list = []
        labels_list = []

        print("[Temperature Scaling] Extracting validation logits for NLL optimization...")
        with torch.no_grad():
            for images, labels, _ in val_loader:
                images = images.to(device)
                logits = model(images)
                logits_list.append(logits.cpu())
                labels_list.append(labels)

        all_logits = torch.cat(logits_list, dim=0)
        all_labels = torch.cat(labels_list, dim=0)

        nll_criterion = nn.CrossEntropyLoss()

        # Compute uncalibrated NLL
        uncalibrated_nll = nll_criterion(all_logits, all_labels).item()

        # Optimize temperature using L-BFGS
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)

        def eval_step():
            optimizer.zero_grad()
            scaled_logits = self.forward(all_logits)
            loss = nll_criterion(scaled_logits, all_labels)
            loss.backward()
            return loss

        optimizer.step(eval_step)

        # Ensure temperature is positive
        with torch.no_grad():
            self.temperature.clamp_(min=0.05, max=10.0)

        calibrated_nll = nll_criterion(self.forward(all_logits), all_labels).item()
        optimal_temp = float(self.temperature.item())

        print(f"[Temperature Scaling] Optimal Temperature T*: {optimal_temp:.4f}")
        print(f"  Uncalibrated Validation NLL: {uncalibrated_nll:.4f}")
        print(f"  Calibrated Validation NLL:   {calibrated_nll:.4f}")
        return optimal_temp


def evaluate_calibration(
    model: nn.Module,
    scaler: Optional[TemperatureScaler],
    dataloader: DataLoader,
    device: torch.device,
    n_bins: int = 10
) -> Dict[str, Any]:
    """
    Evaluates Expected Calibration Error (ECE) and bin gaps.
    Returns metrics dictionary with and without temperature scaling.
    """
    model.eval()
    uncalibrated_probs = []
    calibrated_probs = []
    all_labels = []

    with torch.no_grad():
        for images, labels, _ in dataloader:
            images = images.to(device)
            raw_logits = model(images)

            # Uncalibrated (T = 1.0)
            uncal_p = torch.softmax(raw_logits, dim=1)
            uncalibrated_probs.extend(uncal_p.cpu().tolist())

            # Calibrated (T = T*)
            if scaler is not None:
                cal_logits = scaler(raw_logits)
                cal_p = torch.softmax(cal_logits, dim=1)
                calibrated_probs.extend(cal_p.cpu().tolist())

            all_labels.extend(labels.tolist())

    # Calculate uncalibrated ECE
    uncal_ece_dict = compute_calibration_ece(all_labels, uncalibrated_probs, n_bins=n_bins)

    results = {
        "uncalibrated": {
            "temperature": 1.0,
            "ece": uncal_ece_dict["expected_calibration_error_ece"],
            "is_well_calibrated": uncal_ece_dict["is_well_calibrated"],
            "bin_details": uncal_ece_dict["bin_details"]
        }
    }

    if scaler is not None and calibrated_probs:
        cal_ece_dict = compute_calibration_ece(all_labels, calibrated_probs, n_bins=n_bins)
        temp_val = round(float(scaler.temperature.item()), 4)
        results["calibrated"] = {
            "temperature": temp_val,
            "ece": cal_ece_dict["expected_calibration_error_ece"],
            "is_well_calibrated": cal_ece_dict["is_well_calibrated"],
            "ece_reduction_pct": round(
                ((uncal_ece_dict["expected_calibration_error_ece"] - cal_ece_dict["expected_calibration_error_ece"]) /
                 max(uncal_ece_dict["expected_calibration_error_ece"], 1e-6)) * 100, 2
            ),
            "bin_details": cal_ece_dict["bin_details"]
        }

    return results


def run_full_calibration_pipeline(
    model: nn.Module,
    val_loader: DataLoader,
    test_loader: DataLoader,
    device: torch.device,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Full workflow:
      1. Fits TemperatureScaler on val_loader
      2. Evaluates calibration on test_loader before & after
      3. Saves calibration_metrics.json artifact
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    scaler = TemperatureScaler(initial_temp=1.0)
    optimal_t = scaler.fit(model, val_loader, device)

    # Evaluate on held-out test set
    test_calib = evaluate_calibration(model, scaler, test_loader, device, n_bins=10)
    test_calib["optimal_temperature"] = round(optimal_t, 4)

    calib_file = output_dir / "calibration_metrics.json"
    with open(calib_file, "w", encoding="utf-8") as fp:
        json.dump(test_calib, fp, indent=2)

    print(f"\n[Calibration Summary] Results saved to {calib_file}")
    print(f"  Test ECE Before Calibration (T=1.000): {test_calib['uncalibrated']['ece']:.4f}")
    if "calibrated" in test_calib:
        print(f"  Test ECE After Calibration (T={optimal_t:.3f}): {test_calib['calibrated']['ece']:.4f} "
              f"(Reduction: {test_calib['calibrated']['ece_reduction_pct']}%)")
        print(f"  Calibrated Status: {'Well-Calibrated (ECE < 0.10)' if test_calib['calibrated']['is_well_calibrated'] else 'Sub-optimal'}")

    return test_calib

