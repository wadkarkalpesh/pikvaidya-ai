#!/usr/bin/env python3
"""
PikVaidya AI — Transfer Learning & Model Training Pipeline
==========================================================
Trains vision models (EfficientNet-B0, MobileNetV3, ResNet-50) for crop disease classification.
Features:
 - AdamW optimizer + CosineAnnealingLR
 - Cross-Entropy loss with label smoothing (0.1)
 - Validation Macro-F1 checkpointing
 - Artifact management (best_model.pth, class_mapping.json, training_history.json, config.json)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.data.dataset import SugarcaneDataset, get_transforms
from src.training.models import build_model
from src.evaluation.metrics import compute_classification_metrics


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> Tuple[float, float]:
    """Runs a single training epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels, _ in dataloader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    epoch_loss = running_loss / total
    epoch_acc = correct / total
    return epoch_loss, epoch_acc


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    class_names: List[str],
    device: torch.device
) -> Tuple[float, Dict[str, Any]]:
    """Runs validation and evaluates Macro-F1 and per-class metrics."""
    model.eval()
    running_loss = 0.0
    total = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels, _ in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            total += labels.size(0)

            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    val_loss = running_loss / total
    metrics = compute_classification_metrics(all_labels, all_preds, class_names)
    return val_loss, metrics


def run_training(
    model_name: str,
    data_dir: Path,
    output_dir: Path,
    epochs: int = 15,
    batch_size: int = 32,
    lr: float = 5e-4,
    device_name: str = "auto"
):
    """Executes the full training lifecycle and saves production artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Device selection
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    print(f"\n[Environment] Using computational device: {device}")

    # Load class mapping
    mapping_path = data_dir / "class_mapping.json"
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    class_to_idx = mapping["class_to_idx"]
    class_names = [mapping["idx_to_class"][str(i)] for i in range(len(class_to_idx))]
    num_classes = len(class_names)

    # Initialize Datasets and Loaders
    train_dataset = SugarcaneDataset(str(data_dir / "train_manifest.csv"), transform=get_transforms("train"))
    val_dataset = SugarcaneDataset(str(data_dir / "val_manifest.csv"), transform=get_transforms("val"))

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"[Data] Training samples: {len(train_dataset)} | Validation samples: {len(val_dataset)}")
    print(f"[Data] Classes ({num_classes}): {', '.join(class_names)}")

    # Build model
    model = build_model(model_name, num_classes=num_classes, pretrained=True)
    model.to(device)

    # Training configuration
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    best_val_f1 = 0.0
    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "val_macro_f1": []
    }

    start_time = time.time()
    print(f"\n[Training] Commencing transfer learning for {model.arch_name} ({epochs} epochs)...")
    print("-" * 75)
    print(f"{'Epoch':<8}{'Train Loss':<14}{'Train Acc':<14}{'Val Loss':<14}{'Val Acc':<12}{'Val F1 (Macro)':<16}")
    print("-" * 75)

    for epoch in range(1, epochs + 1):
        t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        v_loss, v_metrics = validate(model, val_loader, criterion, class_names, device)
        scheduler.step()

        v_acc = v_metrics["accuracy"]
        v_f1 = v_metrics["macro_f1"]

        history["train_loss"].append(round(t_loss, 4))
        history["train_acc"].append(round(t_acc, 4))
        history["val_loss"].append(round(v_loss, 4))
        history["val_acc"].append(round(v_acc, 4))
        history["val_macro_f1"].append(round(v_f1, 4))

        is_best = v_f1 > best_val_f1
        flag = " [BEST]" if is_best else ""
        print(f"{epoch:<8}{t_loss:<14.4f}{t_acc * 100:<13.2f}%{v_loss:<14.4f}{v_acc * 100:<11.2f}%{v_f1:<15.4f}{flag}")

        if is_best:
            best_val_f1 = v_f1
            checkpoint = {
                "epoch": epoch,
                "model_name": model.arch_name,
                "state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_macro_f1": v_f1,
                "val_accuracy": v_acc,
                "class_to_idx": class_to_idx,
                "idx_to_class": mapping["idx_to_class"]
            }
            torch.save(checkpoint, output_dir / "best_model.pth")

    duration = time.time() - start_time
    print("-" * 75)
    print(f"[Training Complete] Total elapsed: {duration:.1f}s | Best Validation Macro-F1: {best_val_f1:.4f}")

    # Save artifacts
    with open(output_dir / "training_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    with open(output_dir / "class_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

    config_record = {
        "model_architecture": model.arch_name,
        "epochs": epochs,
        "batch_size": batch_size,
        "initial_learning_rate": lr,
        "optimizer": "AdamW",
        "scheduler": "CosineAnnealingLR",
        "loss_function": "CrossEntropyLoss(label_smoothing=0.1)",
        "num_classes": num_classes,
        "classes": class_names,
        "device": str(device),
        "duration_seconds": round(duration, 2),
        "best_val_macro_f1": round(best_val_f1, 4)
    }
    with open(output_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config_record, f, indent=2)

    print(f"[Artifacts Saved in {output_dir}]:")
    print("   ├── best_model.pth")
    print("   ├── class_mapping.json")
    print("   ├── training_history.json")
    print("   └── config.json\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI Model Trainer")
    parser.add_argument("--model", type=str, default="efficientnet_b0", help="efficientnet_b0, mobilenet_v3, resnet50")
    parser.add_argument("--data-dir", type=str, default="datasets/processed/sugarcane")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-4)
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else Path(f"models/sugarcane/{args.model}")
    run_training(args.model, Path(args.data_dir), out_dir, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
