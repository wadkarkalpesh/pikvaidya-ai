"""
PikVaidya AI — Improved Onion Leaf Pathology Training & Calibration Pipeline
============================================================================
Trains an improved transfer-learned MobileNetV3-Large neural network on the
expanded, standardized, and leakage-free COLD Onion Disease Dataset (5,317 images).

Key Methodological Principles:
1. Strict Leakage Prevention: Zero cross-split parent contamination.
2. Class-Weighted Cross-Entropy: Counteracts class imbalance (especially Purple Blotch).
3. Transfer Learning: ImageNet-v2 pre-trained weights with early backbone feature freezing.
4. Post-Hoc Temperature Scaling: Optimizes scalar T* on validation set logits.
5. Dual-Runtime Export: Saves PyTorch checkpoint and exports sanitized ONNX graph (Opset 18).
6. Rigorous Independent Evaluation: Assesses test metrics on the 797-image unseen test set.
"""

import os
import json
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, classification_report
import onnx
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "onion_dataset" / "processed"
MODEL_DIR = PROJECT_ROOT / "models" / "onion" / "mobilenet_v3"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

REPORTS_DIR = PROJECT_ROOT / "onion_dataset" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 6
LR = 7e-4
WEIGHT_DECAY = 1e-4
NUM_CLASSES = 4

NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]


def get_dataloaders():
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    train_ds = datasets.ImageFolder(str(DATA_DIR / "train"), transform=train_transform)
    val_ds = datasets.ImageFolder(str(DATA_DIR / "val"), transform=eval_transform)
    test_ds = datasets.ImageFolder(str(DATA_DIR / "test"), transform=eval_transform)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Compute inverse class frequencies for balanced loss weighting
    class_counts = [0] * NUM_CLASSES
    for _, label in train_ds.samples:
        class_counts[label] += 1

    total_samples = len(train_ds)
    class_weights = [total_samples / (NUM_CLASSES * count) for count in class_counts]
    class_weights_t = torch.tensor(class_weights, dtype=torch.float32)

    print(f"Dataset Loaded: Train={len(train_ds)}, Val={len(val_ds)}, Test={len(test_ds)}")
    print(f"Class Counts in Train: {dict(zip(train_ds.classes, class_counts))}")
    print(f"Computed Class Weights: {class_weights_t.tolist()}")

    return train_loader, val_loader, test_loader, train_ds.class_to_idx, class_weights_t


def build_improved_mobilenet_v3(num_classes: int = 4) -> nn.Module:
    weights = models.MobileNet_V3_Large_Weights.DEFAULT
    model = models.mobilenet_v3_large(weights=weights)

    # Freeze earlier low-level representation layers (features 0-12)
    # Train high-level inverted residual blocks (features 13-16) and classification head
    for param in model.features[:-4].parameters():
        param.requires_grad = False

    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(),
        nn.Dropout(p=0.25),
        nn.Linear(256, num_classes)
    )
    model.target_conv_layer = model.features[-1]
    return model


def optimize_temperature(model: nn.Module, val_loader: DataLoader, device: torch.device) -> float:
    """Finds optimal temperature scalar T* on validation set using L-BFGS to minimize NLL."""
    model.eval()
    logits_list = []
    labels_list = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            out = model(images)
            logits_list.append(out.cpu())
            labels_list.append(labels)

    all_logits = torch.cat(logits_list, dim=0)
    all_labels = torch.cat(labels_list, dim=0)

    # Optimize single scalar temperature parameter T
    temp = nn.Parameter(torch.ones(1) * 1.5)
    nll_criterion = nn.CrossEntropyLoss()
    optimizer = optim.LBFGS([temp], lr=0.01, max_iter=50)

    def eval_loss():
        optimizer.zero_grad()
        loss = nll_criterion(all_logits / temp, all_labels)
        loss.backward()
        return loss

    optimizer.step(eval_loss)
    optimal_t = float(temp.item())
    print(f"Optimized Temperature Scaling Parameter T*: {optimal_t:.4f}")
    return optimal_t


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Executing Training Pipeline on Compute Device: {device}")

    train_loader, val_loader, test_loader, class_to_idx, class_weights = get_dataloaders()
    idx_to_class = {str(v): k for k, v in class_to_idx.items()}

    model = build_improved_mobilenet_v3(num_classes=NUM_CLASSES)
    model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR,
        weight_decay=WEIGHT_DECAY,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)

    best_val_f1 = 0.0
    best_state_dict = None
    training_history = []

    start_train_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
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

        scheduler.step()
        epoch_train_loss = running_loss / total
        epoch_train_acc = correct / total

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_labels = []

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                val_preds.extend(preds.cpu().numpy())
                val_labels.extend(labels.cpu().numpy())

        epoch_val_loss = val_loss / len(val_labels)
        epoch_val_acc = accuracy_score(val_labels, val_preds)
        epoch_val_f1 = f1_score(val_labels, val_preds, average="macro")
        epoch_duration = time.time() - epoch_start

        print(
            f"Epoch {epoch:02d}/{EPOCHS:02d} [{epoch_duration:.1f}s] - "
            f"Train Loss: {epoch_train_loss:.4f}, Train Acc: {epoch_train_acc*100:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc*100:.2f}%, Val F1: {epoch_val_f1:.4f}"
        )

        history_entry = {
            "epoch": epoch,
            "train_loss": round(epoch_train_loss, 4),
            "train_accuracy": round(epoch_train_acc, 4),
            "val_loss": round(epoch_val_loss, 4),
            "val_accuracy": round(epoch_val_acc, 4),
            "val_f1": round(epoch_val_f1, 4),
            "epoch_duration_seconds": round(epoch_duration, 2),
        }
        training_history.append(history_entry)

        if epoch_val_f1 > best_val_f1:
            best_val_f1 = epoch_val_f1
            best_state_dict = model.state_dict().copy()

    total_training_duration = time.time() - start_train_time
    print(f"Training Complete in {total_training_duration:.1f} seconds. Best Val F1: {best_val_f1:.4f}")

    # Load best weights
    model.load_state_dict(best_state_dict)

    # Optimize Temperature Scaling T*
    optimal_t = optimize_temperature(model, val_loader, device)

    # --------------------------------------------------------------------------
    # Independent Test Evaluation
    # --------------------------------------------------------------------------
    print("=" * 70)
    print("INDEPENDENT REAL-WORLD TEST EVALUATION (797 SAMPLES)")
    print("=" * 70)
    model.eval()
    test_preds = []
    test_labels = []
    latencies = []

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            t0 = time.perf_counter()
            outputs = model(images)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) / images.size(0))
            _, preds = torch.max(outputs, 1)
            test_preds.extend(preds.cpu().numpy())
            test_labels.extend(labels.numpy())

    test_acc = accuracy_score(test_labels, test_preds)
    test_f1 = f1_score(test_labels, test_preds, average="macro")
    test_prec = precision_score(test_labels, test_preds, average="macro", zero_division=0)
    test_rec = recall_score(test_labels, test_preds, average="macro", zero_division=0)
    cm = confusion_matrix(test_labels, test_preds)
    avg_latency_ms = float(np.mean(latencies) * 1000)

    target_names = [idx_to_class[str(i)] for i in range(NUM_CLASSES)]
    cls_report = classification_report(test_labels, test_preds, target_names=target_names, output_dict=True)

    print(f"Test Accuracy:  {test_acc*100:.2f}%")
    print(f"Macro F1 Score: {test_f1:.4f}")
    print(f"Macro Precision: {test_prec:.4f}")
    print(f"Macro Recall:    {test_rec:.4f}")
    print(f"Inference Latency: {avg_latency_ms:.2f} ms/sample")
    print("Confusion Matrix:\n", cm)

    # --------------------------------------------------------------------------
    # Save Model Checkpoint
    # --------------------------------------------------------------------------
    ckpt_path = MODEL_DIR / "best_model.pth"
    torch.save({
        "model_name": "MobileNetV3-Large",
        "crop": "onion",
        "num_classes": NUM_CLASSES,
        "class_to_idx": class_to_idx,
        "idx_to_class": idx_to_class,
        "temperature": optimal_t,
        "metrics": {
            "test_accuracy": round(test_acc, 4),
            "macro_f1": round(test_f1, 4),
            "macro_precision": round(test_prec, 4),
            "macro_recall": round(test_rec, 4),
            "avg_latency_ms": round(avg_latency_ms, 2),
        },
        "state_dict": model.state_dict(),
    }, ckpt_path)
    print(f"Model Checkpoint saved to: {ckpt_path}")

    # Save Class Mapping
    with open(MODEL_DIR / "class_mapping.json", "w") as f:
        json.dump({"class_to_idx": class_to_idx, "idx_to_class": idx_to_class}, f, indent=2)

    # Save Metrics JSON
    with open(MODEL_DIR / "test_metrics.json", "w") as f:
        json.dump({
            "test_accuracy": round(test_acc, 4),
            "macro_f1": round(test_f1, 4),
            "macro_precision": round(test_prec, 4),
            "macro_recall": round(test_rec, 4),
            "avg_latency_ms": round(avg_latency_ms, 2),
            "confusion_matrix": cm.tolist(),
            "per_class": cls_report,
        }, f, indent=2)

    # Save Detailed Training Report
    with open(REPORTS_DIR / "training_report.json", "w") as f:
        json.dump({
            "architecture": "MobileNetV3-Large",
            "epochs": EPOCHS,
            "learning_rate": LR,
            "total_duration_seconds": round(total_training_duration, 2),
            "history": training_history,
            "optimal_temperature": optimal_t,
            "final_test_metrics": {
                "test_accuracy": round(test_acc, 4),
                "macro_f1": round(test_f1, 4),
                "macro_precision": round(test_prec, 4),
                "macro_recall": round(test_rec, 4),
                "avg_latency_ms": round(avg_latency_ms, 2),
            },
            "confusion_matrix": cm.tolist(),
            "classes": target_names,
        }, f, indent=2)

    # --------------------------------------------------------------------------
    # Export to Sanitized ONNX Opset 18
    # --------------------------------------------------------------------------
    print("Exporting improved model to ONNX (Opset 18)...")
    onnx_path = MODEL_DIR / "model.onnx"
    dummy_input = torch.randn(1, 3, 224, 224, device=device)

    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )

    # Sanitize ONNX model against value_info collisions
    onnx_model = onnx.load(str(onnx_path))
    init_names = {init.name for init in onnx_model.graph.initializer}
    new_vi = [vi for vi in onnx_model.graph.value_info if vi.name not in init_names]
    del onnx_model.graph.value_info[:]
    onnx_model.graph.value_info.extend(new_vi)
    onnx.checker.check_model(onnx_model)
    onnx.save(onnx_model, str(onnx_path))
    print(f"Sanitized ONNX exported successfully: {onnx_path}")

    # Verify ONNX Runtime forward pass
    ort_session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_out = ort_session.run(None, {"input": dummy_input.cpu().numpy()})[0]
    torch_out = model(dummy_input).detach().cpu().numpy()
    cos_sim = float(np.dot(ort_out.flatten(), torch_out.flatten()) / (
        np.linalg.norm(ort_out.flatten()) * np.linalg.norm(torch_out.flatten())
    ))
    print(f"ONNX Runtime vs PyTorch FP32 Cosine Similarity: {cos_sim:.6f}")


if __name__ == "__main__":
    main()

