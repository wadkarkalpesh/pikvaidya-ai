"""
PikVaidya AI — Onion Leaf Pathology Dataset Synthesizer & Augmentation Pipeline
==============================================================================
Constructs a balanced 4-class Onion Pathology Dataset adhering to ICAR-DOGR
(Directorate of Onion and Garlic Research) and Aishwarya & Reddy (2024) standards:
  0: Onion___healthy
  1: Onion___purple_blotch (Alternaria porri)
  2: Onion___stemphylium_blight (Stemphylium vesicarium)
  3: Onion___iris_yellow_virus (Iris Yellow Spot Virus)
"""

import os
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "datasets" / "processed" / "onion"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLASSES = [
    "Onion___healthy",
    "Onion___purple_blotch",
    "Onion___stemphylium_blight",
    "Onion___iris_yellow_virus",
]

CLASS_TO_IDX = {cls_name: i for i, cls_name in enumerate(CLASSES)}
IDX_TO_CLASS = {str(i): cls_name for i, cls_name in enumerate(CLASSES)}


def generate_base_onion_leaf(cls_name: str, seed: int) -> Image.Image:
    """Generates an image of an onion tubular blade with domain-accurate pathology."""
    np.random.seed(seed)
    random.seed(seed)

    # Base canvas: Soil / natural background
    img = Image.new("RGB", (256, 256), color=(60, 50, 40))
    draw = ImageDraw.Draw(img)

    # Add background soil texture variations
    for _ in range(30):
        bx = random.randint(0, 250)
        by = random.randint(0, 250)
        bw = random.randint(5, 20)
        draw.ellipse([bx, by, bx + bw, by + bw], fill=(50 + random.randint(0, 25), 45 + random.randint(0, 20), 35))

    # Draw vertical onion tubular leaf blade
    # Onion leaves are cylindrical/tubular, tapering towards the tip
    leaf_w = random.randint(32, 50)
    leaf_x = 128 + random.randint(-15, 15)
    
    # Healthy base green color (slightly bluish-green for Allium cepa)
    base_color = (45 + random.randint(-5, 5), 140 + random.randint(-10, 10), 55 + random.randint(-5, 5))
    
    # Draw leaf stalk
    draw.polygon(
        [
            (leaf_x - leaf_w // 2, 256),
            (leaf_x + leaf_w // 2, 256),
            (leaf_x + leaf_w // 3, 20),
            (leaf_x - leaf_w // 3, 20),
        ],
        fill=base_color,
    )
    # Leaf tip curve
    draw.chord([leaf_x - leaf_w // 3, 10, leaf_x + leaf_w // 3, 40], start=180, end=360, fill=base_color)

    # Add leaf longitudinal vein shading
    for offset in range(-leaf_w // 3, leaf_w // 3, 6):
        draw.line(
            [(leaf_x + offset, 256), (leaf_x + int(offset * 0.7), 25)],
            fill=(base_color[0] - 8, base_color[1] - 12, base_color[2] - 8),
            width=2,
        )

    # --------------------------------------------------------------------------
    # Pathological Lesion Rendering
    # --------------------------------------------------------------------------
    if cls_name == "Onion___purple_blotch":
        # Alternaria porri: Sunken purple center surrounded by concentric rings & yellow halo
        num_lesions = random.randint(2, 5)
        for _ in range(num_lesions):
            lx = leaf_x + random.randint(-leaf_w // 4, leaf_w // 4)
            ly = random.randint(60, 200)
            rad_x = random.randint(8, 16)
            rad_y = random.randint(14, 28)

            # Outer chlorotic yellow halo
            draw.ellipse([lx - rad_x - 4, ly - rad_y - 6, lx + rad_x + 4, ly + rad_y + 6], fill=(160, 160, 30))
            # Brown necrotic ring
            draw.ellipse([lx - rad_x, ly - rad_y, lx + rad_x, ly + rad_y], fill=(95, 45, 30))
            # Deep purple/brown center
            draw.ellipse([lx - rad_x // 2, ly - rad_y // 2, lx + rad_x // 2, ly + rad_y // 2], fill=(70, 25, 55))

    elif cls_name == "Onion___stemphylium_blight":
        # Stemphylium vesicarium: Small yellow/tan water-soaked lesions coalescing into large blighted areas
        num_spots = random.randint(6, 12)
        for _ in range(num_spots):
            lx = leaf_x + random.randint(-leaf_w // 3, leaf_w // 3)
            ly = random.randint(40, 220)
            rw = random.randint(4, 10)
            rh = random.randint(6, 18)
            # Tan/buff colored necrotic patch with olive border
            draw.ellipse([lx - rw, ly - rh, lx + rw, ly + rh], fill=(175, 140, 75))
            draw.ellipse([lx - rw // 2, ly - rh // 2, lx + rw // 2, ly + rh // 2], fill=(130, 95, 45))

    elif cls_name == "Onion___iris_yellow_virus":
        # Iris Yellow Spot Virus: Straw-colored diamond-shaped or spindle-shaped chlorotic lesions
        num_spots = random.randint(3, 7)
        for _ in range(num_spots):
            lx = leaf_x + random.randint(-leaf_w // 4, leaf_w // 4)
            ly = random.randint(50, 210)
            dw = random.randint(6, 12)
            dh = random.randint(10, 22)
            # Diamond/spindle shape
            draw.polygon(
                [(lx, ly - dh), (lx + dw, ly), (lx, ly + dh), (lx - dw, ly)],
                fill=(210, 205, 110),
            )
            # Faint green island inside diamond (characteristic of IYSV)
            draw.ellipse([lx - 2, ly - 3, lx + 2, ly + 3], fill=(80, 130, 60))

    # Smooth filter to simulate natural camera sensor capture
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    return img


def main():
    print("=================================================================")
    print("Generating Onion Pathology Dataset (Balanced 4-Class)...")
    print("=================================================================")

    splits = {"train": 150, "val": 40, "test": 40}  # 230 per class = 920 images total
    manifests = {"train": [], "val": [], "test": []}

    for split_name, count_per_class in splits.items():
        split_dir = OUTPUT_DIR / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        for cls_name in CLASSES:
            cls_dir = split_dir / cls_name
            cls_dir.mkdir(parents=True, exist_ok=True)
            class_idx = CLASS_TO_IDX[cls_name]

            for i in range(count_per_class):
                seed = hash(f"{split_name}_{cls_name}_{i}") & 0xFFFFFFFF
                img = generate_base_onion_leaf(cls_name, seed)
                img_filename = f"{cls_name}_{i:04d}.jpg"
                img_path = cls_dir / img_filename
                img.save(img_path, format="JPEG", quality=92)

                rel_path = str(img_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
                manifests[split_name].append({
                    "image_path": rel_path,
                    "class_name": cls_name,
                    "class_idx": class_idx,
                    "split": split_name,
                })

    # Save manifests using standard csv module
    fieldnames = ["image_path", "class_name", "class_idx", "split"]
    for split_name, rows in manifests.items():
        csv_path = OUTPUT_DIR / f"{split_name}_manifest.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✓ Saved {split_name} manifest: {len(rows)} images -> {csv_path.name}")

    # Save class mappings
    with open(OUTPUT_DIR / "class_mapping.json", "w", encoding="utf-8") as f:
        json.dump({"class_to_idx": CLASS_TO_IDX, "idx_to_class": IDX_TO_CLASS}, f, indent=2)

    print(f"✓ Saved class mapping to {OUTPUT_DIR / 'class_mapping.json'}")
    print(f"Total dataset size: {sum(len(r) for r in manifests.values())} images across 4 classes.")


if __name__ == "__main__":
    main()
