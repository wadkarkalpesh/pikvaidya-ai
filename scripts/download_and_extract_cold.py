"""
PikVaidya AI — COLD Onion Leaf Disease Dataset Ingestion Script
==============================================================
Downloads authentic real-world onion foliar disease images from Hugging Face
(Project-AgML/COLD_onion_leaf_disease_classification, licensed under CC-BY-4.0).
Preserves raw provenance, metadata, and ground truth labels.
"""

import io
import os
import hashlib
from pathlib import Path
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "onion_dataset" / "raw" / "cold_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

COLD_RAW_PARQUET_URL = (
    "https://huggingface.co/api/datasets/Project-AgML/COLD_onion_leaf_disease_classification/"
    "parquet/raw/train/0.parquet"
)

# Label mapping according to dataset card specifications
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
    print(f"Downloading COLD raw parquet from {COLD_RAW_PARQUET_URL}...")
    df = pd.read_parquet(COLD_RAW_PARQUET_URL)
    print(f"Downloaded {len(df)} raw samples. Extracting images...")

    saved_count = 0
    corrupted_count = 0
    records = []

    for idx, row in df.iterrows():
        raw_label = row["label"]
        orig_label_name = LABEL_MAP.get(raw_label, f"unknown_{raw_label}")
        std_label = STANDARDIZED_MAP.get(orig_label_name, "unknown")

        class_dir = RAW_DIR / std_label
        class_dir.mkdir(parents=True, exist_ok=True)

        img_dict = row["image"]
        img_bytes = img_dict["bytes"]
        orig_filename = img_dict.get("path") or f"cold_raw_{idx:04d}.jpg"

        # Verification
        try:
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                pil_img.verify()
            with Image.open(io.BytesIO(img_bytes)) as pil_img:
                width, height = pil_img.size
                mode = pil_img.mode

            sha256 = hashlib.sha256(img_bytes).hexdigest()
            filename = f"cold_raw_{std_label}_{idx:04d}_{sha256[:8]}.jpg"
            target_path = class_dir / filename
            target_path.write_bytes(img_bytes)

            records.append({
                "idx": idx,
                "filename": filename,
                "orig_filename": orig_filename,
                "orig_label": orig_label_name,
                "std_label": std_label,
                "width": width,
                "height": height,
                "mode": mode,
                "sha256": sha256,
            })
            saved_count += 1
        except Exception as e:
            print(f"Error extracting image {idx}: {e}")
            corrupted_count += 1

    print(f"Extracted {saved_count} verified images. Corrupted: {corrupted_count}")
    return records


if __name__ == "__main__":
    main()

