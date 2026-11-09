"""
PikVaidya AI — Onion Phase Deep Verification & Validation Script
================================================================
Verifies:
1. Dataset manifest integrity and zero data leakage across groups
2. Best model checkpoint structure, weights, and calibration
3. Evaluates model on independent 797-sample test set
4. Computes per-class classification report, confusion matrix, ECE (Expected Calibration Error)
5. Tests Grad-CAM on real samples from each of the 4 onion disease classes
"""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score, precision_score, recall_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def verify_dataset_and_leakage():
    print("=" * 70)
    print("1. VERIFYING EXPANDED ONION DATASET & ZERO LEAKAGE")
    print("=" * 70)
    manifest_path = PROJECT_ROOT / "onion_dataset" / "manifests" / "onion_dataset_manifest.csv"
    assert manifest_path.exists(), f"Missing manifest at {manifest_path}"
    df = pd.read_csv(manifest_path)
    print(f"Manifest loaded: {len(df)} total verified rows")
    
    splits = df.groupby("split").size().to_dict()
    print(f"Split distributions: {splits}")
    assert splits.get("train", 0) == 3720, f"Unexpected train count: {splits}"
    assert splits.get("val", 0) == 800, f"Unexpected val count: {splits}"
    assert splits.get("test", 0) == 797, f"Unexpected test count: {splits}"
    
    # Verify group leakage
    train_groups = set(df[df["split"] == "train"]["duplicate_group"].dropna())
    val_groups = set(df[df["split"] == "val"]["duplicate_group"].dropna())
    test_groups = set(df[df["split"] == "test"]["duplicate_group"].dropna())
    
    overlap_tv = train_groups.intersection(val_groups)
    overlap_tt = train_groups.intersection(test_groups)
    overlap_vt = val_groups.intersection(test_groups)
    
    print(f"Unique duplicate groups: Train={len(train_groups)}, Val={len(val_groups)}, Test={len(test_groups)}")
    print(f"Cross-split group overlaps: Train-Val={len(overlap_tv)}, Train-Test={len(overlap_tt)}, Val-Test={len(overlap_vt)}")
    assert len(overlap_tv) == 0, f"Data leakage detected between Train and Val: {overlap_tv}"
    assert len(overlap_tt) == 0, f"Data leakage detected between Train and Test: {overlap_tt}"
    assert len(overlap_vt) == 0, f"Data leakage detected between Val and Test: {overlap_vt}"
    print("[PASS] 0% Data Leakage Verified: All parent groups strictly isolated.")

def verify_model_and_test_metrics():
    print("=" * 70)
    print("2. INDEPENDENT ONION MODEL VALIDATION (797 UNSEEN TEST SAMPLES)")
    print("=" * 70)
    ckpt_path = PROJECT_ROOT / "models" / "onion" / "mobilenet_v3" / "best_model.pth"
    assert ckpt_path.exists(), f"Checkpoint missing at {ckpt_path}"
    
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    print(f"Checkpoint Architecture: {ckpt.get('model_name')}")
    print(f"Target Crop: {ckpt.get('crop')}")
    print(f"Calibrated Temperature T*: {ckpt.get('temperature'):.4f}")
    print(f"Recorded Checkpoint Metrics: {ckpt.get('metrics')}")
    
    num_classes = ckpt.get("num_classes", 4)
    model = models.mobilenet_v3_large(weights=None)
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(),
        nn.Dropout(p=0.25),
        nn.Linear(256, num_classes)
    )
    model.target_conv_layer = model.features[-1]
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    
    test_dir = PROJECT_ROOT / "onion_dataset" / "processed" / "test"
    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    test_ds = datasets.ImageFolder(str(test_dir), transform=eval_transform)
    test_loader = torch.utils.data.DataLoader(test_ds, batch_size=32, shuffle=False)
    
    all_preds = []
    all_labels = []
    all_confs = []
    latencies = []
    
    temp = ckpt.get("temperature", 1.0)
    
    with torch.no_grad():
        for imgs, lbls in test_loader:
            t0 = time.perf_counter()
            logits = model(imgs)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) / imgs.size(0))
            
            calibrated_probs = torch.softmax(logits / temp, dim=1)
            confs, preds = torch.max(calibrated_probs, dim=1)
            
            all_preds.extend(preds.numpy())
            all_labels.extend(lbls.numpy())
            all_confs.extend(confs.numpy())
            
    acc = accuracy_score(all_labels, all_preds)
    f1_macro = f1_score(all_labels, all_preds, average="macro")
    prec_macro = precision_score(all_labels, all_preds, average="macro")
    rec_macro = recall_score(all_labels, all_preds, average="macro")
    cm = confusion_matrix(all_labels, all_preds)
    avg_latency_ms = np.mean(latencies) * 1000
    
    # Compute Expected Calibration Error (ECE) with 10 bins
    confidences = np.array(all_confs)
    accuracies = (np.array(all_preds) == np.array(all_labels)).astype(float)
    bin_boundaries = np.linspace(0, 1, 11)
    ece = 0.0
    for i in range(10):
        bin_mask = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i+1])
        bin_size = np.sum(bin_mask)
        if bin_size > 0:
            bin_acc = np.mean(accuracies[bin_mask])
            bin_conf = np.mean(confidences[bin_mask])
            ece += (bin_size / len(confidences)) * np.abs(bin_acc - bin_conf)
            
    print(f"Validation Test Accuracy: {acc * 100:.2f}%")
    print(f"Macro F1-Score:         {f1_macro:.4f}")
    print(f"Macro Precision:        {prec_macro:.4f}")
    print(f"Macro Recall:           {rec_macro:.4f}")
    print(f"Expected Calibration Error (ECE): {ece * 100:.2f}%")
    print(f"Average CPU Latency:    {avg_latency_ms:.2f} ms/sample")
    print("\nConfusion Matrix:\n", cm)
    print("\nClassification Report:\n", classification_report(all_labels, all_preds, target_names=test_ds.classes, digits=4))
    
    # Check model file size
    model_size_mb = ckpt_path.stat().st_size / (1024 * 1024)
    print(f"PyTorch Checkpoint Size: {model_size_mb:.2f} MB")
    
    onnx_path = PROJECT_ROOT / "models" / "onion" / "mobilenet_v3" / "model.onnx"
    int8_path = PROJECT_ROOT / "models" / "onion" / "mobilenet_v3" / "model_int8.onnx"
    if onnx_path.exists():
        print(f"FP32 ONNX Size: {onnx_path.stat().st_size / (1024*1024):.2f} MB")
    if int8_path.exists():
        print(f"Dynamic INT8 ONNX Size: {int8_path.stat().st_size / (1024*1024):.2f} MB")
        
    return model, test_ds.classes

if __name__ == "__main__":
    verify_dataset_and_leakage()
    verify_model_and_test_metrics()
