#!/usr/bin/env python3
"""
PikVaidya AI — PyTorch Dataset & Transform Pipeline
===================================================
Provides resilient data loading for audited agricultural crops.
Includes:
 - Normalization using ImageNet statistics
 - Field-realistic augmentations (RandomRotation, ColorJitter, RandomHorizontalFlip)
 - Robust PIL image loader
"""

import csv
from pathlib import Path
from typing import Callable, Optional, Tuple
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms as T


# Standard ImageNet normalization parameters
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def get_transforms(split: str = "train", img_size: int = 224) -> Callable:
    """Returns PyTorch transforms according to dataset split."""
    if split == "train":
        return T.Compose([
            T.Resize((img_size, img_size)),
            T.RandomHorizontalFlip(p=0.5),
            T.RandomVerticalFlip(p=0.3),
            T.RandomRotation(degrees=15),
            T.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
    else:
        return T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])


class SugarcaneDataset(Dataset):
    """Custom PyTorch dataset loaded from a CSV manifest."""
    def __init__(self, manifest_csv: str, transform: Optional[Callable] = None):
        self.samples = []
        with open(manifest_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.samples.append({
                    "image_path": row["image_path"],
                    "class_name": row["class_name"],
                    "label_idx": int(row["label_idx"]),
                    "is_field": row.get("is_field_image", "True").lower() == "true"
                })
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, str]:
        item = self.samples[idx]
        image_path = item["image_path"]
        label = item["label_idx"]

        with Image.open(image_path) as img:
            img = img.convert("RGB")
            if self.transform:
                img_tensor = self.transform(img)
            else:
                img_tensor = T.ToTensor()(img)

        return img_tensor, label, image_path
