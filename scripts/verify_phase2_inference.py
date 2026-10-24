import sys
import csv
import math
from pathlib import Path
import torch
from PIL import Image

sys.path.insert(0, "backend")
from app.services.model_service import model_service

print("--- PHASE 2: VERIFY MODEL INFERENCE ---")
model_service.load_model()
print(f"Model service loaded: is_loaded={model_service.is_loaded}")
print(f"Model version: {model_service.model_version}")
print(f"Device: {model_service.device}")
print(f"Classes: {model_service.idx_to_class}")

manifest = Path("datasets/processed/sugarcane/test_manifest.csv")
with open(manifest, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Sample 1 per class
samples = {}
for r in rows:
    if r["class_name"] not in samples:
        samples[r["class_name"]] = r["image_path"]

print("\n--- Testing 5 Representative Test Leaf Samples ---")
for cls, img_path_str in samples.items():
    p = Path(img_path_str)
    assert p.exists(), f"Image does not exist: {p}"
    raw_bytes = p.read_bytes()
    res = model_service.predict(raw_bytes, crop="sugarcane", generate_gradcam=False)
    
    # Check numerical finiteness
    assert math.isfinite(res["confidence"]), "Confidence not finite"
    assert all(math.isfinite(v) for v in res["class_scores"].values()), "Class scores not finite"
    
    # Check probability bounds
    scores = res["class_scores"]
    prob_sum = sum(scores.values())
    assert 0.99 <= prob_sum <= 1.01, f"Probabilities sum ({prob_sum}) out of bounds"
    assert all(0.0 <= v <= 1.0 for v in scores.values()), "Probabilities outside [0, 1]"
    
    match = cls == res["predicted_class"]
    print(f"GT: {cls:8s} | Pred: {res['predicted_class']:8s} | Conf: {res['confidence']:.4f} | Match: {match}")
    print(f"   Distribution: {scores}")

# Test arbitrary dimensions (aspect ratio, small, large)
print("\n--- Testing Non-standard Image Dimensions & Aspect Ratios ---")
dim_tests = [(100, 100), (640, 480), (1920, 1080), (50, 400)]
for w, h in dim_tests:
    img = Image.new("RGB", (w, h), color=(50, 150, 50))
    tensor, pil_img = model_service.preprocess_image(img)
    assert tensor.shape == (3, 224, 224), f"Preprocessed tensor shape mismatch: {tensor.shape}"
    with torch.no_grad():
        logits = model_service.model(tensor.unsqueeze(0).to(model_service.device))
        assert logits.shape == (1, 5)
        assert torch.all(torch.isfinite(logits))
    print(f"Dimension test ({w}x{h}) -> Tensor shape {tuple(tensor.shape)} -> PASS")

print("\n--- PHASE 2 VERIFICATION COMPLETE: ALL CHECKS PASSED ---")
