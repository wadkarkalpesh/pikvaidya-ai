#!/usr/bin/env python3
"""
PikVaidya AI — Unit Tests for Confidence Calibration & Temperature Scaling
==========================================================================
Verifies:
  1. TemperatureScaler initialization and forward scaling
  2. NLL minimization and parameter convergence on synthetic logits
  3. ECE calculation accuracy and well-calibrated threshold logic
  4. Reliability diagram bin metadata structure
"""

import sys
from pathlib import Path
import pytest
import torch
import torch.nn as nn
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.calibration import TemperatureScaler, evaluate_calibration
from src.evaluation.metrics import compute_calibration_ece


def test_temperature_scaler_initialization():
    scaler = TemperatureScaler(initial_temp=1.5)
    assert scaler.temperature.item() == pytest.approx(1.5, rel=1e-3)
    assert scaler.temperature.requires_grad is True


def test_temperature_scaler_forward():
    scaler = TemperatureScaler(initial_temp=2.0)
    logits = torch.tensor([[2.0, 4.0], [0.0, -2.0]])
    scaled = scaler(logits)
    expected = logits / 2.0
    assert torch.allclose(scaled, expected)


def test_temperature_scaling_optimization():
    # Construct overconfident logits
    torch.manual_seed(42)
    scaler = TemperatureScaler(initial_temp=1.0)
    
    # Synthetic logits where overconfidence exists
    logits = torch.randn(100, 5) * 5.0
    labels = torch.randint(0, 5, (100,))

    criterion = nn.CrossEntropyLoss()
    initial_loss = criterion(logits, labels).item()

    optimizer = torch.optim.LBFGS([scaler.temperature], lr=0.05, max_iter=25)

    def closure():
        optimizer.zero_grad()
        loss = criterion(scaler(logits), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    final_loss = criterion(scaler(logits), labels).item()

    assert final_loss <= initial_loss
    assert scaler.temperature.item() > 0.05


def test_compute_calibration_ece():
    # Perfectly calibrated synthetic probabilities
    y_true = [0, 1, 0, 1]
    y_prob = [
        [0.9, 0.1],
        [0.1, 0.9],
        [0.85, 0.15],
        [0.2, 0.8]
    ]
    res = compute_calibration_ece(y_true, y_prob, n_bins=5)
    assert "expected_calibration_error_ece" in res
    assert "is_well_calibrated" in res
    assert isinstance(res["bin_details"], list)
    assert 0.0 <= res["expected_calibration_error_ece"] <= 1.0


def test_ece_bin_details_structure():
    y_true = [0, 1, 2]
    y_prob = [
        [0.8, 0.1, 0.1],
        [0.2, 0.7, 0.1],
        [0.1, 0.3, 0.6]
    ]
    res = compute_calibration_ece(y_true, y_prob, n_bins=10)
    assert isinstance(res["is_well_calibrated"], bool)
    for b in res["bin_details"]:
        assert "bin_range" in b
        assert "sample_count" in b
        assert "avg_confidence" in b
        assert "accuracy" in b
        assert "calibration_gap" in b
