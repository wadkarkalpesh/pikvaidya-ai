import os
import sys
import glob
import json
import random
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

random.seed(42)
torch.manual_seed(42)

sc_files = glob.glob('data/raw/sugarcane/**/*.jpeg', recursive=True) + glob.glob('data/raw/sugarcane/**/*.jpg', recursive=True)
tm_files = glob.glob('data/raw/tomato/**/*.jpg', recursive=True)
on_files = glob.glob('onion_dataset/processed/**/*.jpg', recursive=True)

random.shuffle(sc_files)
random.shuffle(tm_files)
random.shuffle(on_files)

# 200 train and 100 test per crop
train_items = [(f, 0) for f in sc_files[:200]] + [(f, 1) for f in tm_files[:200]] + [(f, 2) for f in on_files[:200]]
test_items = [(f, 0) for f in sc_files[200:300]] + [(f, 1) for f in tm_files[200:300]] + [(f, 2) for f in on_files[200:300]]

print(f"Total train: {len(train_items)}, Total test: {len(test_items)}", flush=True)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

class LeafListDataset(Dataset):
    def __init__(self, items, transform):
        self.items = items
        self.transform = transform
        
    def __len__(self):
        return len(self.items)
        
    def __getitem__(self, idx):
        path, label = self.items[idx]
        try:
            img = Image.open(path).convert('RGB')
            tensor = self.transform(img)
            return tensor, label
        except Exception:
            return torch.zeros(3, 224, 224), label

train_loader = DataLoader(LeafListDataset(train_items, transform), batch_size=32, shuffle=False, num_workers=0)
test_loader = DataLoader(LeafListDataset(test_items, transform), batch_size=32, shuffle=False, num_workers=0)

mobilenet = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
mobilenet.eval()
feature_extractor = mobilenet.features
pool = nn.AdaptiveAvgPool2d(1)

def extract_all(loader, desc=""):
    print(f"Extracting {desc} with DataLoader batching...", flush=True)
    feats, labels = [], []
    with torch.no_grad():
        for batch_x, batch_y in loader:
            f = pool(feature_extractor(batch_x)).squeeze(-1).squeeze(-1)
            feats.append(f.numpy())
            labels.append(batch_y.numpy())
    import numpy as np
    return np.vstack(feats), np.concatenate(labels)

X_train, y_train = extract_all(train_loader, "train")
X_test, y_test = extract_all(test_loader, "test")

print("Fitting logistic regression classifier...", flush=True)
clf = LogisticRegression(max_iter=1000, C=1.0)
clf.fit(X_train, y_train)

test_preds = clf.predict(X_test)
acc = accuracy_score(y_test, test_preds)
report = classification_report(y_test, test_preds, target_names=['sugarcane', 'tomato', 'onion'], output_dict=True)
print(f"Crop Classifier Test Accuracy: {acc*100:.2f}%", flush=True)
print(classification_report(y_test, test_preds, target_names=['sugarcane', 'tomato', 'onion']), flush=True)

out_dir = Path("models/crop_detector")
out_dir.mkdir(parents=True, exist_ok=True)

# Build pure PyTorch sequential model
linear = nn.Linear(576, 3)
linear.weight.data = torch.from_numpy(clf.coef_).float()
linear.bias.data = torch.from_numpy(clf.intercept_).float()

crop_model = nn.Sequential(
    feature_extractor,
    pool,
    nn.Flatten(),
    linear
)
crop_model.eval()

torch.save({
    "state_dict": crop_model.state_dict(),
    "class_mapping": {"0": "sugarcane", "1": "tomato", "2": "onion"},
    "accuracy": acc,
    "report": report
}, out_dir / "crop_detector.pth")

with open(out_dir / "detector_metrics.json", "w") as f:
    json.dump({"test_accuracy": acc, "classification_report": report}, f, indent=2)

print("Saved PyTorch crop detector to models/crop_detector/crop_detector.pth", flush=True)

