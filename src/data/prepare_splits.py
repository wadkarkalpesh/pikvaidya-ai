#!/usr/bin/env python3
"""
PikVaidya AI — Dataset Deduplication & Stratified Splitting Engine
=================================================================
Processes the audited Sugarcane dataset:
 - Prunes exact cryptographic duplicates (210 files)
 - Verifies 5 classes: Healthy, Mosaic, RedRot, Rust, Yellow
 - Creates deterministic 70% Train / 15% Validation / 15% Test stratified splits
 - Exports manifest CSVs and class mapping JSON to datasets/processed/sugarcane/
"""

import os
import csv
import json
import random
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def deduplicate_dataset(raw_dir: Path) -> Dict[str, List[Path]]:
    """Scans class directories and retains only unique images by MD5 hash."""
    unique_class_images = defaultdict(list)
    seen_hashes = set()
    total_scanned = 0
    duplicate_count = 0

    class_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
    
    for cdir in class_dirs:
        class_name = cdir.name
        image_files = sorted([f for f in cdir.glob("*.*") if f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
        
        for img_path in image_files:
            total_scanned += 1
            with open(img_path, "rb") as fp:
                h = hashlib.md5(fp.read()).hexdigest()
            
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_class_images[class_name].append(img_path)
            else:
                duplicate_count += 1

    print(f"[Deduplication] Total images scanned: {total_scanned}")
    print(f"[Deduplication] Exact duplicates pruned: {duplicate_count}")
    print(f"[Deduplication] Unique images retained: {sum(len(v) for v in unique_class_images.values())}")
    for c, imgs in sorted(unique_class_images.items()):
        print(f"   - Class '{c}': {len(imgs)} unique images")

    return unique_class_images


def create_stratified_splits(
    unique_images: Dict[str, List[Path]],
    output_dir: Path,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Creates stratified train, val, and test splits with fixed seed."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-5, "Ratios must sum to 1.0"
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    classes = sorted(list(unique_images.keys()))
    class_to_idx = {c: i for i, c in enumerate(classes)}
    idx_to_class = {i: c for i, c in enumerate(classes)}

    train_rows, val_rows, test_rows = [], [], []

    for cname, paths in unique_images.items():
        shuffled = paths.copy()
        random.shuffle(shuffled)
        
        n_total = len(shuffled)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        
        train_paths = shuffled[:n_train]
        val_paths = shuffled[n_train:n_train + n_val]
        test_paths = shuffled[n_train + n_val:]

        for p in train_paths:
            train_rows.append({"image_path": str(p.resolve()), "class_name": cname, "label_idx": class_to_idx[cname], "is_field_image": True})
        for p in val_paths:
            val_rows.append({"image_path": str(p.resolve()), "class_name": cname, "label_idx": class_to_idx[cname], "is_field_image": True})
        for p in test_paths:
            test_rows.append({"image_path": str(p.resolve()), "class_name": cname, "label_idx": class_to_idx[cname], "is_field_image": True})

    # Save manifest CSVs
    fieldnames = ["image_path", "class_name", "label_idx", "is_field_image"]
    for split_name, rows in [("train", train_rows), ("val", val_rows), ("test", test_rows)]:
        csv_path = output_dir / f"{split_name}_manifest.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[Export] Saved {split_name} manifest: {csv_path.name} ({len(rows)} samples)")

    # Save class mappings
    mapping_path = output_dir / "class_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as fp:
        json.dump({"class_to_idx": class_to_idx, "idx_to_class": idx_to_class}, fp, indent=2)
    print(f"[Export] Saved class mapping: {mapping_path.name}")

    return class_to_idx, idx_to_class


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PikVaidya AI Data Splitter")
    parser.add_argument("--raw-dir", type=str, default="data/raw/sugarcane")
    parser.add_argument("--output-dir", type=str, default="datasets/processed/sugarcane")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    unique_imgs = deduplicate_dataset(Path(args.raw_dir))
    create_stratified_splits(unique_imgs, Path(args.output_dir), seed=args.seed)
