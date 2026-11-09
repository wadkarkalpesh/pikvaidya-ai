"""
PikVaidya AI — COLD Onion Augmented Dataset Ingestion Script
===========================================================
Downloads the 4,502 verified augmented samples from COLD on Hugging Face.
Stores them in onion_dataset/raw/cold_augmented/ with original class labels.
"""

import io
import os
import hashlib
from pathlib import Path
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUG_DIR = PROJECT_ROOT / "onion_dataset" / "raw" / "cold_augmented"
AUG_DIR.mkdir(parents=True, exist_ok=True)

COLD_AUG_PARQUET_URL = (
    "https://huggingface.co/api/datasets/Project-AgML/COLD_onion_leaf_disease_classification/"
    "parquet/augmented/train/0.parquet"
)

LABEL_MAP = {
    0: "Iris yellow virus",
    1: "Stemphylium leaf blight and collectrichum leaf blight",
    2: "healthy",
    3: "purple blotch",
}

STANDARDIZED_MAP = {
    "Iris yellow virus": "Onion___iris_yellow_virus",
    "Stemphylium leaf blight and collectrichum leaf blight": "Onion___stemphylium_blight",
    "healthy": "Onion___healthy",
    "purple blotch": "Onion___purple_blotch",
}


def main():
    print(f"Downloading COLD augmented parquet from {COLD_AUG_PARQUET_URL}...")
    df = pd.read_parquet(COLD_AUG_PARQUET_URL)
    print(f"Downloaded {len(df)} augmented samples. Extracting images...")

    saved_count = 0
    corrupted_count = 0

    for idx, row in df.iterrows():
        raw_label = row["label"]
        orig_label_name = LABEL_MAP.get(raw_label, f"unknown_{raw_label}")
        std_label = STANDARDIZED_MAP.get(orig_label_name, "unknown")

        class_dir = AUG_DIR / std_label
        class_dir.mkdir(parents=True, exist_ok=True)

        img_dict = row["image"]
        img_bytes = img_dict["bytes"]

        try:
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                pil_img.verify()

            sha256 = hashlib.sha256(img_bytes).hexdigest()
            filename = f"cold_aug_{std_label}_{idx:05d}_{sha256[:8]}.jpg"
            target_path = class_dir / filename
            target_path.write_bytes(img_bytes)
            saved_count += 1
            if saved_count % 1000 == 0:
                print(f"Extracted {saved_count} / {len(df)} images...")
        except Exception as e:
            print(f"Error extracting augmented image {idx}: {e}")
            corrupted_count += 1

    print(f"Successfully extracted {saved_count} augmented images. Corrupted: {corrupted_count}")


if __name__ == "__main__":
    main()

