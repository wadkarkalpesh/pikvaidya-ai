#!/usr/bin/env python3
"""
PikVaidya AI — Complete Machine Learning Pipeline Training Engine
=================================================================
Trains EfficientNet-B0 for Sugarcane crop pathology diagnosis:
  - 5 classes: Healthy, Mosaic, RedRot, Rust, Yellow
  - ImageNet-1K pretrained weights
  - Balanced class weighting in CrossEntropyLoss with label smoothing (0.1)
  - Two-stage progressive transfer learning:
      Stage 1: Frozen backbone classifier head alignment (AdamW, lr=1e-3)
      Stage 2: Top convolutional block fine-tuning (features[-1], lr=1e-4)
  - Cosine annealing learning rate scheduling
  - Early stopping tracking Validation Macro-F1
  - Artifact preservation in dedicated pipeline directory (no overwriting original checkpoint)
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from typing import Dict, Any, Tuple, List

# Ensure project root in sys.path
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


def set_seed(seed: int = 42):
    """Ensures deterministic reproducibility across CPU and GPU runtimes."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def calculate_class_weights(dataset: SugarcaneDataset, num_classes: int) -> torch.Tensor:
    """Computes balanced inverse-frequency class weights for cross-entropy loss."""
    class_counts = torch.zeros(num_classes, dtype=torch.float32)
    for sample in dataset.samples:
        class_counts[sample["label_idx"]] += 1.0

    total_samples = len(dataset.samples)
    # Balanced weighting: w_c = N / (num_classes * N_c)
    weights = total_samples / (num_classes * class_counts)
    # Normalize weights so mean is 1.0
    weights = weights / weights.mean()
    return weights


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> Tuple[float, float]:
    """Executes single training epoch."""
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


def evaluate_split(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    class_names: List[str],
    device: torch.device
) -> Tuple[float, Dict[str, Any]]:
    """Evaluates loss, accuracy, Macro-F1, and per-class metrics."""
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

    split_loss = running_loss / total
    metrics = compute_classification_metrics(all_labels, all_preds, class_names)
    return split_loss, metrics


def run_pipeline_training(
    manifest_dir: Path,
    output_dir: Path,
    seed: int = 42,
    batch_size: int = 32,
    head_epochs: int = 3,
    finetune_epochs: int = 2,
    head_lr: float = 1e-3,
    finetune_lr: float = 1e-4,
    device_arg: str = "auto"
) -> Dict[str, Any]:
    """
    Executes full multi-stage transfer learning training pipeline.
    """
    set_seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve Device
    if device_arg == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
        device_str = "CUDA (NVIDIA GPU)"
    elif device_arg == "cpu":
        device = torch.device("cpu")
        device_str = "CPU"
    else:  # "auto"
        if torch.cuda.is_available():
            device = torch.device("cuda")
            device_str = "CUDA (NVIDIA GPU)"
        else:
            device = torch.device("cpu")
            device_str = "CPU (Fallback: torch compiled without CUDA)"

    print("\n" + "=" * 80)
    print("  PIKVAIDYA AI: COMPLETE MODEL TRAINING PIPELINE")
    print(f"  Architecture: EfficientNet-B0 | Hardware: {device_str}")
    print(f"  Artifact Output: {output_dir.resolve()}")
    print("=" * 80)

    # 2. Load Manifests & Datasets
    mapping_path = manifest_dir / "class_mapping.json"
    with open(mapping_path, "r", encoding="utf-8") as fp:
        mapping = json.load(fp)
    class_to_idx = mapping["class_to_idx"]
    class_names = [mapping["idx_to_class"][str(i)] for i in range(len(class_to_idx))]
    num_classes = len(class_names)

    train_dataset = SugarcaneDataset(str(manifest_dir / "train_manifest.csv"), transform=get_transforms("train"))
    val_dataset = SugarcaneDataset(str(manifest_dir / "val_manifest.csv"), transform=get_transforms("val"))

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"\n[Dataset Distribution]")
    print(f"  Train Samples:      {len(train_dataset)}")
    print(f"  Validation Samples: {len(val_dataset)}")
    print(f"  Classes ({num_classes}):      {', '.join(class_names)}")

    # 3. Class Imbalance Handling
    class_weights = calculate_class_weights(train_dataset, num_classes).to(device)
    print(f"[Loss Function] Class Weights for CrossEntropy: {[round(w, 3) for w in class_weights.tolist()]}")
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)

    # 4. Build Model with Pretrained ImageNet Weights
    print("\n[Model Initialization] Loading EfficientNet-B0 with ImageNet-1K pretrained weights...")
    model = build_model("efficientnet_b0", num_classes=num_classes, pretrained=True)
    model.to(device)

    history = {
        "epoch": [],
        "stage": [],
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "val_macro_f1": [],
        "learning_rate": []
    }

    best_val_f1 = 0.0
    best_epoch = 0
    total_epochs = head_epochs + finetune_epochs
    start_time = time.time()

    # -------------------------------------------------------------
    # STAGE 1: Classifier Head Warmup (Backbone Features Frozen)
    # -------------------------------------------------------------
    print(f"\n[Stage 1/2] Training Classifier Head ({head_epochs} epochs, lr={head_lr})...")
    for param in model.features.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True

    optimizer_head = torch.optim.AdamW(model.classifier.parameters(), lr=head_lr, weight_decay=1e-4)
    scheduler_head = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer_head, T_max=head_epochs, eta_min=1e-5)

    print("-" * 80)
    print(f"{'Epoch':<8}{'Stage':<12}{'Train Loss':<14}{'Train Acc':<13}{'Val Loss':<13}{'Val Acc':<11}{'Val Macro-F1':<14}")
    print("-" * 80)

    for ep in range(1, head_epochs + 1):
        t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer_head, device)
        v_loss, v_metrics = evaluate_split(model, val_loader, criterion, class_names, device)
        scheduler_head.step()

        v_acc = v_metrics["accuracy"]
        v_f1 = v_metrics["macro_f1"]
        cur_lr = optimizer_head.param_groups[0]["lr"]

        history["epoch"].append(ep)
        history["stage"].append("Head_Warmup")
        history["train_loss"].append(round(t_loss, 4))
        history["train_acc"].append(round(t_acc, 4))
        history["val_loss"].append(round(v_loss, 4))
        history["val_acc"].append(round(v_acc, 4))
        history["val_macro_f1"].append(round(v_f1, 4))
        history["learning_rate"].append(round(cur_lr, 6))

        is_best = v_f1 > best_val_f1
        flag = " [BEST]" if is_best else ""
        print(f"{ep:<8}{'Head':<12}{t_loss:<14.4f}{t_acc*100:<12.2f}%{v_loss:<13.4f}{v_acc*100:<10.2f}%{v_f1:<14.4f}{flag}")

        if is_best:
            best_val_f1 = v_f1
            best_epoch = ep
            _save_checkpoint(output_dir, model, optimizer_head, ep, v_f1, v_acc, class_to_idx, mapping["idx_to_class"])

    # -------------------------------------------------------------
    # STAGE 2: Top Convolutional Block Fine-Tuning (features[-1])
    # -------------------------------------------------------------
    print(f"\n[Stage 2/2] Fine-tuning Top Conv Block features[-1] + Classifier ({finetune_epochs} epochs, lr={finetune_lr})...")
    # Unfreeze final conv stage (block 8)
    for param in model.features[-1].parameters():
        param.requires_grad = True

    trainable_params = [
        {"params": model.features[-1].parameters(), "lr": finetune_lr * 0.5},
        {"params": model.classifier.parameters(), "lr": finetune_lr}
    ]
    optimizer_ft = torch.optim.AdamW(trainable_params, weight_decay=1e-4)
    scheduler_ft = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer_ft, T_max=finetune_epochs, eta_min=1e-6)

    for ep in range(head_epochs + 1, total_epochs + 1):
        t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer_ft, device)
        v_loss, v_metrics = evaluate_split(model, val_loader, criterion, class_names, device)
        scheduler_ft.step()

        v_acc = v_metrics["accuracy"]
        v_f1 = v_metrics["macro_f1"]
        cur_lr = optimizer_ft.param_groups[1]["lr"]

        history["epoch"].append(ep)
        history["stage"].append("FineTune_TopConv")
        history["train_loss"].append(round(t_loss, 4))
        history["train_acc"].append(round(t_acc, 4))
        history["val_loss"].append(round(v_loss, 4))
        history["val_acc"].append(round(v_acc, 4))
        history["val_macro_f1"].append(round(v_f1, 4))
        history["learning_rate"].append(round(cur_lr, 6))

        is_best = v_f1 > best_val_f1
        flag = " [BEST]" if is_best else ""
        print(f"{ep:<8}{'FineTune':<12}{t_loss:<14.4f}{t_acc*100:<12.2f}%{v_loss:<13.4f}{v_acc*100:<10.2f}%{v_f1:<14.4f}{flag}")

        if is_best:
            best_val_f1 = v_f1
            best_epoch = ep
            _save_checkpoint(output_dir, model, optimizer_ft, ep, v_f1, v_acc, class_to_idx, mapping["idx_to_class"])

    total_time = time.time() - start_time
    print("-" * 80)
    print(f"[Training Complete] Total elapsed: {total_time:.1f}s ({total_time/60:.2f} min)")
    print(f"  Best Validation Macro-F1: {best_val_f1:.4f} (Achieved at Epoch {best_epoch})")
    print(f"  Best Model Checkpoint:    {output_dir / 'best_model.pth'}")
    print("-" * 80)

    # 5. Save Training Artifacts
    config_dict = {
        "model_architecture": "EfficientNet-B0",
        "num_classes": num_classes,
        "input_resolution": [224, 224],
        "pretrained_weights": "EfficientNet_B0_Weights.DEFAULT (ImageNet-1K)",
        "seed": seed,
        "batch_size": batch_size,
        "total_epochs": total_epochs,
        "head_epochs": head_epochs,
        "finetune_epochs": finetune_epochs,
        "head_lr": head_lr,
        "finetune_lr": finetune_lr,
        "optimizer": "AdamW",
        "weight_decay": 1e-4,
        "scheduler": "CosineAnnealingLR",
        "loss_function": "CrossEntropyLoss with balanced class weights and label_smoothing=0.1",
        "class_weights": [round(w, 4) for w in class_weights.tolist()],
        "execution_device": device_str,
        "training_duration_seconds": round(total_time, 2),
        "best_epoch": best_epoch,
        "best_val_macro_f1": round(best_val_f1, 4)
    }

    with open(output_dir / "training_config.json", "w", encoding="utf-8") as fp:
        json.dump(config_dict, fp, indent=2)

    with open(output_dir / "training_history.json", "w", encoding="utf-8") as fp:
        json.dump(history, fp, indent=2)

    with open(output_dir / "class_mapping.json", "w", encoding="utf-8") as fp:
        json.dump(mapping, fp, indent=2)

    return config_dict


def _save_checkpoint(output_dir, model, optimizer, epoch, val_f1, val_acc, class_to_idx, idx_to_class):
    """Safely saves model checkpoint with full metadata."""
    ckpt = {
        "epoch": epoch,
        "model_name": "EfficientNet-B0",
        "state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_macro_f1": float(val_f1),
        "val_accuracy": float(val_acc),
        "class_to_idx": class_to_idx,
        "idx_to_class": idx_to_class
    }
    torch.save(ckpt, output_dir / "best_model.pth")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI — Complete ML Pipeline Training")
    parser.add_argument("--manifest-dir", type=str, default="datasets/processed/sugarcane")
    parser.add_argument("--output-dir", type=str, default="models/sugarcane/efficientnet_b0/pipeline_trained")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--head-epochs", type=int, default=3)
    parser.add_argument("--finetune-epochs", type=int, default=2)
    parser.add_argument("--head-lr", type=float, default=1e-3)
    parser.add_argument("--finetune-lr", type=float, default=1e-4)
    parser.add_argument("--device", type=str, default="auto")
    args = parser.parse_args()

    run_pipeline_training(
        manifest_dir=Path(args.manifest_dir),
        output_dir=Path(args.output_dir),
        seed=args.seed,
        batch_size=args.batch_size,
        head_epochs=args.head_epochs,
        finetune_epochs=args.finetune_epochs,
        head_lr=args.head_lr,
        finetune_lr=args.finetune_lr,
        device_arg=args.device
    )

