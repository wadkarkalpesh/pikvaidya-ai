"""
PikVaidya AI — Onion Leaf Pathology Training, Calibration & ONNX Pipeline
========================================================================
Fine-tunes MobileNetV3-Large on the 4-class Onion Pathology Dataset:
  0: Onion___healthy
  1: Onion___iris_yellow_virus
  2: Onion___purple_blotch
  3: Onion___stemphylium_blight
Computes temperature scaling (T*), evaluates metrics, and exports to ONNX.
"""

import json
import time
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
import onnx
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "datasets" / "processed" / "onion"
MODEL_DIR = PROJECT_ROOT / "models" / "onion" / "mobilenet_v3"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 5
LR = 5e-4
NUM_CLASSES = 4

# ImageNet normalization
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]


def get_dataloaders():
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
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

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    return train_loader, val_loader, test_loader, train_ds.class_to_idx


def build_mobilenet_v3(num_classes: int) -> nn.Module:
    weights = models.MobileNet_V3_Large_Weights.DEFAULT
    model = models.mobilenet_v3_large(weights=weights)

    # Freeze early backbone feature blocks for stable transfer learning
    for param in model.features[:-3].parameters():
        param.requires_grad = False

    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes)
    )
    model.target_conv_layer = model.features[-1]
    return model


def compute_temperature_scaling(model: nn.Module, val_loader: DataLoader, device: torch.device) -> float:
    """Finds optimal temperature T* minimizing negative log-likelihood on validation logits."""
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

    # Grid search for T in [0.5, 3.0]
    best_t = 1.0
    best_loss = float("inf")
    criterion = nn.CrossEntropyLoss()

    for t_val in np.linspace(0.5, 2.5, 41):
        scaled_logits = all_logits / t_val
        loss = criterion(scaled_logits, all_labels).item()
        if loss < best_loss:
            best_loss = loss
            best_t = float(t_val)

    return round(best_t, 4)


def main():
    print("=================================================================")
    print("Training Onion Pathology Classifier (MobileNetV3-Large Transfer)...")
    print("=================================================================")

    device = torch.device("cpu")
    train_loader, val_loader, test_loader, class_to_idx = get_dataloaders()
    idx_to_class = {str(v): k for k, v in class_to_idx.items()}

    model = build_mobilenet_v3(num_classes=NUM_CLASSES).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)

    best_val_acc = 0.0
    best_state_dict = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        t0 = time.time()
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        epoch_loss = running_loss / total
        epoch_acc = correct / total

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                preds = torch.argmax(outputs, dim=1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total
        dt = time.time() - t0
        print(f"Epoch {epoch}/{EPOCHS} [{dt:.1f}s] - Train Loss: {epoch_loss:.4f}, Train Acc: {epoch_acc:.2%}, Val Acc: {val_acc:.2%}")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_state_dict = model.state_dict()

    # Load best checkpoint
    model.load_state_dict(best_state_dict)

    # Compute Temperature Scaling
    t_star = compute_temperature_scaling(model, val_loader, device)
    print(f"\n✓ Calibrated Temperature T* = {t_star:.4f}")

    # Evaluate on Test Set
    model.eval()
    test_preds, test_targets = [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images) / t_star
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            test_preds.extend(preds)
            test_targets.extend(labels.numpy())

    test_preds_arr = np.array(test_preds)
    test_targets_arr = np.array(test_targets)

    test_acc = float(accuracy_score(test_targets_arr, test_preds_arr))
    test_f1 = float(f1_score(test_targets_arr, test_preds_arr, average="macro"))
    test_prec = float(precision_score(test_targets_arr, test_preds_arr, average="macro", zero_division=0))
    test_rec = float(recall_score(test_targets_arr, test_preds_arr, average="macro", zero_division=0))

    print(f"\n=================================================================")
    print(f"ONION TEST RESULTS (Calibrated MobileNetV3-Large):")
    print(f"  - Test Accuracy:   {test_acc:.2%}")
    print(f"  - Macro F1-Score:  {test_f1:.4f}")
    print(f"  - Macro Precision: {test_prec:.4f}")
    print(f"  - Macro Recall:    {test_rec:.4f}")
    print(f"=================================================================")

    # Save Best PyTorch Model Checkpoint
    checkpoint_data = {
        "model_name": "MobileNetV3-Large",
        "crop": "onion",
        "num_classes": NUM_CLASSES,
        "class_to_idx": class_to_idx,
        "idx_to_class": idx_to_class,
        "temperature": t_star,
        "metrics": {
            "test_accuracy": test_acc,
            "macro_f1": test_f1,
            "macro_precision": test_prec,
            "macro_recall": test_rec,
        },
        "state_dict": best_state_dict,
    }
    ckpt_path = MODEL_DIR / "best_model.pth"
    torch.save(checkpoint_data, ckpt_path)
    print(f"✓ Saved PyTorch checkpoint: {ckpt_path.name} ({ckpt_path.stat().st_size / (1024*1024):.2f} MB)")

    # Save Class Mapping
    with open(MODEL_DIR / "class_mapping.json", "w", encoding="utf-8") as f:
        json.dump({"class_to_idx": class_to_idx, "idx_to_class": idx_to_class}, f, indent=2)

    # Save Metrics
    with open(MODEL_DIR / "test_metrics.json", "w", encoding="utf-8") as f:
        json.dump(checkpoint_data["metrics"], f, indent=2)

    # --------------------------------------------------------------------------
    # Export to ONNX
    # --------------------------------------------------------------------------
    onnx_path = MODEL_DIR / "model.onnx"
    dummy_input = torch.randn(1, 3, 224, 224)
    filtered_state = {k: v for k, v in best_state_dict.items() if not k.startswith("target_conv_layer")}
    model.load_state_dict(filtered_state, strict=False)
    model.eval()

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
    print(f"✓ Exported Onion ONNX Model: {onnx_path.name} ({onnx_path.stat().st_size / (1024*1024):.2f} MB)")

    # Verify ONNX Runtime Parity
    ort_session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_out = ort_session.run(None, {"input": dummy_input.numpy()})[0]
    with torch.no_grad():
        torch_out = model(dummy_input).numpy()
    cosine_sim = float(
        np.dot(torch_out.flatten(), ort_out.flatten())
        / (np.linalg.norm(torch_out) * np.linalg.norm(ort_out))
    )
    print(f"✓ ONNX Numerical Parity Cosine Similarity: {cosine_sim:.6f}")
    assert cosine_sim > 0.999


if __name__ == "__main__":
    main()
