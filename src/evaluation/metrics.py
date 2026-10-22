#!/usr/bin/env python3
"""
PikVaidya AI — Model Evaluation & Calibration Metrics Suite
===========================================================
Calculates empirical performance metrics:
 - Per-class Precision, Recall, F1-Score, and Support
 - Global Macro-F1, Weighted-F1, and Accuracy
 - 5x5 Confusion Matrix (Counts & Normalized)
 - Model Calibration: Expected Calibration Error (ECE) across 10 confidence bins
 - In-field slice evaluation
"""

from typing import Dict, List, Any, Tuple
import numpy as np


def compute_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
    class_names: List[str]
) -> Dict[str, Any]:
    """Calculates per-class precision, recall, F1, and aggregate macro scores."""
    num_classes = len(class_names)
    y_t = np.array(y_true)
    y_p = np.array(y_pred)
    total_samples = len(y_t)

    # 1. Confusion Matrix
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_t, y_p):
        cm[t, p] += 1

    per_class = {}
    precisions, recalls, f1s = [], [], []

    for i, cname in enumerate(class_names):
        tp = cm[i, i]
        fp = np.sum(cm[:, i]) - tp
        fn = np.sum(cm[i, :]) - tp
        support = np.sum(cm[i, :])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

        per_class[cname] = {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
            "support": int(support)
        }

    macro_precision = np.mean(precisions)
    macro_recall = np.mean(recalls)
    macro_f1 = np.mean(f1s)
    accuracy = np.trace(cm) / total_samples if total_samples > 0 else 0.0

    return {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(macro_precision), 4),
        "macro_recall": round(float(macro_recall), 4),
        "macro_f1": round(float(macro_f1), 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist()
    }


def compute_calibration_ece(
    y_true: List[int],
    y_prob: List[List[float]],
    n_bins: int = 10
) -> Dict[str, Any]:
    """
    Computes Expected Calibration Error (ECE) across n_bins confidence intervals.
    ECE measures the alignment between predicted probabilities and empirical accuracy.
    """
    probs = np.array(y_prob)
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == np.array(y_true))

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    bin_details = []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            abs_diff = np.abs(avg_confidence_in_bin - accuracy_in_bin)
            ece += abs_diff * prop_in_bin
            bin_details.append({
                "bin_range": f"{bin_lower:.1f}-{bin_upper:.1f}",
                "sample_count": int(np.sum(in_bin)),
                "avg_confidence": round(float(avg_confidence_in_bin), 4),
                "accuracy": round(float(accuracy_in_bin), 4),
                "calibration_gap": round(float(abs_diff), 4)
            })

    return {
        "expected_calibration_error_ece": round(float(ece), 4),
        "is_well_calibrated": bool(ece < 0.10),
        "bin_details": bin_details
    }
